import sys
from io import StringIO
from pydantic import Field, PositiveInt
import re
import pandas as pd
import numpy as np
from api.helpers.openai_helpers import OpenAIBaseModel
from typing import Optional
from api.helpers.publish import upload_dwca, register_dataset_and_endpoint
import datetime
import uuid
import utm


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
    Run python code using `exec(code, globals={'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np, 'uuid': uuid, 'datetime': datetime, 're': re, 'utm': utm}, {})`. 
    I.e., you have access to an environment with those libraries and a Django database with models `Table` and `Dataset`. You cannot import anything else.
    E.g. code: `table = Table.objects.get(id=df_id); print(table.df.to_string()); dataset = Dataset.objects.get(id=1);` etc
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
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np, 'uuid': uuid, 'datetime': datetime, 're': re, 'utm': utm }
            combined_context = globals.copy()
            combined_context.update(locals)
            exec(code, combined_context, combined_context)  # See https://github.com/python/cpython/issues/86084
            stdout_value = new_stdout.getvalue()
            
            if stdout_value:
                result = stdout_value
            else:
                result = f"Executed successfully without errors."
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return str(result)[:8000]


class RollBack(OpenAIBaseModel):
    """USE WITH CAUTION! Resets to the original dataframes loaded into pandas from the Excel sheet uploaded by the user. ALL CHANGES WILL BE UNDONE. Use as a last resort if data columns have been accidentally deleted or lost."""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        agent = Agent.objects.get(id=self.agent_id)
        # agent.dataset.table_set.all().delete()


class SetBasicMetadata(OpenAIBaseModel):
    """Sets the title and description (Metadata) for a Dataset via an Agent, returns a success message or an error message"""
    agent_id: PositiveInt = Field(...)
    title: str = Field(..., description="A short but descriptive title for the dataset as a whole")
    description: str = Field(..., description="A longer description of what the dataset contains, including any important information about why the data was gathered (e.g. for a study) as well as how it was gathered.")
    user_language: str = Field('English', description="Note down if the user wants to speak in a particular language. Default is English.") 
    structure_notes: Optional[str] = Field(None, description="Optional - Use to note any significant data structural problems or oddities.") 
    suitable_for_publication_on_gbif: Optional[bool] = Field(default=True, description="An OPTIONAL boolean field, set to false if the data is deemed unsuitable for publication on GBIF.")

    def run(self):
        try:
            from api.models import Agent
            agent = Agent.objects.get(id=self.agent_id)
            dataset = agent.dataset
            dataset.title = self.title
            dataset.description = self.description
            if self.structure_notes:
                dataset.structure_notes = self.structure_notes
            if self.user_language != 'English':
                dataset.user_language = self.user_language
            if not self.suitable_for_publication_on_gbif:
                print('Rejecting dataset')
                dataset.rejected_at = datetime.datetime.now()
            dataset.save()
            return 'Basic Metadata has been successfully set.'
        except Exception as e:
            print('There has been an error with SetBasicMetadata')
            return repr(e)[:2000]


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
            tables = dataset.table_set.all()
            core_table = next((table for table in tables if 'occurrenceID' in table.df.columns), tables[0])
            extension_tables = [table for table in tables if table != core_table]
            mof_table =  extension_tables[0] if extension_tables else None
            if mof_table:
                url = upload_dwca(core_table.df, dataset.title, dataset.description, mof_table.df)
            else:
                url = upload_dwca(core_table.df, dataset.title, dataset.description)
            dataset.dwca_url = url
            gbif_url = register_dataset_and_endpoint(dataset.title, dataset.description, dataset.dwca_url)
            dataset.published_at = datetime.datetime.now()
            # import pdb; pdb.set_trace()
            dataset.save()
            return(f'Successfully published. GBIF URL: {gbif_url}, Darwin core archive upload: {url}')
        except Exception as e:
            return repr(e)[:2000]


