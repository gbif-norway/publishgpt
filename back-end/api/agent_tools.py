import sys
from io import StringIO
from pydantic import Field, PositiveInt
import re
import pandas as pd
import numpy as np
from api.helpers.openai_helpers import OpenAIBaseModel
from datetime import datetime


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


class Python(OpenAIBaseModel):
    """
    Run python code using `exec(code, globals={'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np}, {})`, i.e. with access to pandas (pd), numpy (np), and Django database ORM models `Table` and `Dataset`
    E.g. `df_obj = Table.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Edit, delete or create new Table objects as required - remember to save changes to the database (e.g. `df_obj.save()`). 
    - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters 
    - IMPORTANT NOTE #1: State does not persist - Every time this function is called, the slate is wiped clean and you will not have access to any objects created previously.
    - IMPORTANT NOTE #2: If you merge or create a new Table based on old Tables, tidy up after yourself and delete any irrelevant/out of date Tables.
    """
    code: str = Field(..., description="String containing valid python code to be executed in `exec()`")

    def run(self, function_message):
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", self.code)
        code = re.sub(r"(\s|`)*$", "", code)
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        result = ''
        try:
            from api.models import Dataset, Table

            locals = {}
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np }
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


class SetAgentTaskToComplete(OpenAIBaseModel):
    """Mark an Agent's task as complete"""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            agent.completed_at = datetime.now()
            agent.save()
            print('Marking as complete...')
            return f'Task marked as complete for agent id {self.agent_id} .'
        except Exception as e:
            return repr(e)[:2000]


class PublishDwC(OpenAIBaseModel):
    """To be used as the final step for publishing a dataset which is standardised to Darwin Core"""
    dataset_id: PositiveInt = Field(...)

    def run(self):
        pass

