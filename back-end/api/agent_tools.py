import sys
from io import StringIO
from pydantic import Field, PositiveInt
import re
import pandas as pd
import numpy as np
from api.helpers.openai_helpers import OpenAIBaseModel
from typing import Optional
from api.helpers.publish import upload_dwca
import datetime
import uuid


def trim_dataframe(df):
    # Replace empty spaces with NaN
    df.replace('', np.nan, inplace=True)

    # Get the bounds where the non-NaN values start and end
    rows = np.where(df.notna().any(axis=1))[0]
    cols = np.where(df.notna().any(axis=0))[0]

    trimmed_df = df.iloc[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

    # If the first column is just a list of numbers from 0+ or 1+, it is meaningless, drop it
    first_column = trimmed_df.iloc[:, 0]
    if first_column.is_monotonic_increasing and first_column.min() in [0, 1] and np.all(np.diff(first_column) == 1):
        trimmed_df = trimmed_df.drop(trimmed_df.columns[0], axis=1)

    return trimmed_df.fillna('')
 
def extract_sub_tables(df, min_rows=2):
    all_null_rows = df.isnull().all(axis=1)
    start = 0
    tables = []
    for i, is_null in enumerate(all_null_rows):
        if is_null:
            if i - start >= min_rows:
                tables.append(df.iloc[start:i])
            start = i + 1
    if len(df) - start >= min_rows:
        tables.append(df.iloc[start:])
    return [trim_dataframe(t) for t in tables]

class BasicExtractEmptyBoundaryTables(OpenAIBaseModel):
    """
    This works by looking for blank rows and columns. NB - Should only be used as a first pass, and further checks should be carried out. 
    If only one Table is found (i.e., there are no sub tables), it returns False. 
    If multiple Tables are found, the old composite Table is deleted and the new Tables are saved - the total number of new Tables, new Table snapshots and new Table ids are returned.
    """
    table_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Table
        try:
            table = Table.objects.get(id=self.table_id)
            sub_tables = extract_sub_tables(table.df)
            text = False

            if len(sub_tables) > 1:
                distinct_tables = []
                for idx, new_df in enumerate(sub_tables):
                    new_table = Table.objects.create(dataset=table.dataset, title=f'{table.title} - {idx}', df=new_df)
                    distinct_tables.append(new_table)

                snapshots = '\n\n'.join([f'Sub-table #{idx} - (Table.id: {d.id})\n{d.str_snapshot}' for idx, d in enumerate(distinct_tables)])
                if len(snapshots) > 4000:
                    snapshots = snapshots[0:4000] + '\n...'
                text = f'Table id {self.table_id} divided into {len(distinct_tables)} new, separate tables:\n{snapshots}\n\n'

                table.delete()
            if text:
                print(f'Extract Sub Tables results: {text}')
            return text
        except Exception as e:
            return repr(e)[:2000]


class ValidateDwCTerms(OpenAIBaseModel):
    """
    Checks that column names for a given Table comply with the Darwin Core standard
    Returns a list of column names which are incorrect. 
    """
    table_id: PositiveInt = Field(...)

    def run(self):
        pass


class Python(OpenAIBaseModel):
    """
    Run python code using `exec(code, globals={'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np, 'uuid': uuid, 'datetime': datetime, 're': re}, {})`. 
    I.e., you have access to an environment with pandas (pd), numpy (np), uuid, datetime, re and a Django database with models `Table` and `Dataset`. DO NOT import other modules.
    E.g. `table = Table.objects.get(id=df_id); print(table.df.to_string()); dataset = Dataset.objects.get(id=1);` etc
    Notes: - Edit, delete or create new Table objects as required - remember to save changes to the database (e.g. `table.save()`). 
    - Use print() if you want to see output - a string of stdout, truncated to 2000 chars 
    - IMPORTANT NOTE #1: State does not persist - Every time this function is called, the slate is wiped clean and you will not have access to objects created previously.
    - IMPORTANT NOTE #2: If you merge or create a new Table based on old Tables, tidy up after yourself and delete irrelevant/out of date Tables.
    """
    code: str = Field(..., description="String containing valid python code to be executed in `exec()`")

    def run(self):
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", self.code)
        code = re.sub(r"(\s|`)*$", "", code)
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        result = ''
        try:
            from api.models import Dataset, Table

            locals = {}
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np, 'uuid': uuid, 'datetime': datetime, 're': re }
            exec(code, globals, locals)
            stdout_value = new_stdout.getvalue()
            
            if stdout_value:
                result = stdout_value
            else:
                result = f"Executed successfully without errors."
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return f'`{code}` executed, result: {str(result)[:2000]}'


class SetBasicMetadata(OpenAIBaseModel):
    """Sets the title and description (Metadata) for a Dataset via an Agent, returns a success message or an error message"""
    agent_id: PositiveInt = Field(...)
    title: str = Field(..., description="A short but descriptive title for the dataset as a whole")
    description: str = Field(..., description="A longer description of what the dataset contains, including any important information about why the data was gathered (e.g. for a study) as well as how it was gathered.")
    structure_notes: Optional[str] = Field(None, description="Optional - Use to note any significant data structural problems or oddities.") 
    suitable_for_publication_on_gbif: Optional[bool] = Field(default=True, description="An OPTIONAL boolean field, set to false if the data is deemed unsuitable for publication on GBIF.")

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            dataset = agent.dataset
            dataset.title = self.title
            dataset.description = self.description
            dataset.structure_notes = self.structure_notes
            if not self.suitable_for_publication_on_gbif:
                print('rejecting dataset')
                dataset.rejected_at = datetime.datetime.now()
            dataset.save()
            SetAgentTaskToComplete(agent_id=self.agent_id).run()
            return 'Basic Metadata has been successfully set and Agent Task has been set to complete'
        except Exception as e:
            return repr(e)[:2000]


class RenameColumnsWithUserInput(OpenAIBaseModel):
    pass


class SetAgentTaskToComplete(OpenAIBaseModel):
    """Mark an Agent's task as complete"""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            agent.completed_at = datetime.datetime.now()
            agent.save()
            print('Marking as complete...')
            return f'Task marked as complete for agent id {self.agent_id} .'
        except Exception as e:
            return repr(e)[:2000]


class RejectDataset(OpenAIBaseModel):
    """Have an agent reject a dataset"""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            dataset = agent.dataset
            dataset.rejected_at = datetime.datetime.now()
            dataset.save()
            print('Rejecting dataset as unsuitable')
            return f'Dataset rejected for publication by agent id {self.agent_id} .'
        except Exception as e:
            return repr(e)[:2000]


class PublishDwC(OpenAIBaseModel):
    """
    The final step required to publish the user's data to GBIF. 
    Generates a darwin core archive and uploads it to a server, then registers it with the GBIF API. 
    At the moment publishes the test GBIF platform, not production.
    Returns the GBIF URL to the
    """
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            dataset = agent.dataset
            tables = dataset.table_set
            core_table = next((table for table in tables if 'occurrenceID' in table.df.columns), tables[0])
            extension_tables = [table for table in tables if table != core_table]
            mof_table =  extension_tables[0] if extension_tables else None
            url = upload_dwca(core_table.df, dataset.title, dataset.description, mof_table.df)
            dataset.dwca_url = url
            dataset.published_at = datetime.datetime.now()
            dataset.save()
            print(f'Uploaded to minio and published: {url}')
            return url
        except Exception as e:
            return repr(e)[:2000]


