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
    Notes: - Edit, delete or create new Table objects as required - remember to save changes to the database (e.g. `df_obj.save()`). A backup of all Table objects is made before running your code, so it is possible to roll back.
    - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters 
    - IMPORTANT: State does not persist - Every time this function is called, the slate is wiped clean and you will not have access to any objects created previously.
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

            # Make identical duplicate of all the active tables, used for displaying changes to the user but also acts as backups
            duplicate_ids = function_message.agent.dataset.backup_tables_and_get_ids()

            locals = {}
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np }
            exec(code, globals, locals)
            stdout_value = new_stdout.getvalue()
            
            # Duplicate ids have to be passed to the backups, as it's not possible to retrieve them otherwise, unless the models are refactored... which perhaps it should be
            self.handle_table_backups(function_message, duplicate_ids)

            if stdout_value:
                result = stdout_value
            else:
                result = f"Executed successfully without errors."
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return f'`{code}` executed, result: {str(result)[:2000]}'

    @classmethod
    def handle_table_backups(cls, function_message, duplicate_ids):
        from api.models import Table, MessageTableAssociation

        new_tables = function_message.agent.dataset.active_tables
        duplicates = Table.objects.filter(id__in=duplicate_ids)

        # Check for deleted tables, soft delete them and link them to the message
        for backup_table in duplicates.filter(temporary_duplicate_of=None):
            backup_table.soft_delete()
            MessageTableAssociation.objects.create(table=backup_table, message=function_message, operation=MessageTableAssociation.Operation.DELETE)

        # Check for newly created tables, and link to message
        for new_table in [t for t in new_tables if t.id not in duplicates.values_list('temporary_duplicate_of__id', flat=True)]:
            MessageTableAssociation.objects.create(table=new_table, message=function_message, operation=MessageTableAssociation.Operation.CREATE)
        
        # Check for updated tables which haven't been soft deleted
        remaining_tables = duplicates.exclude(temporary_duplicate_of=None)
        for backup_table in remaining_tables:
            updated_table = backup_table.temporary_duplicate_of
            unchanged = backup_table.df.equals(updated_table.df)
            if unchanged:
                backup_table.delete()  # No changes have happened, we don't need to store the backup
            else:
                # Replace the original Table with the backup so we don't have to change any foreign keys
                updated_df = updated_table.df.copy()
                updated_table.df = backup_table.df.copy()
                updated_table.stale_at = datetime.now()
                updated_table.save()

                backup_table.temporary_duplicate_of = None  # Hmm... do we want to actually keep track of which table inherits from which?
                backup_table.df = updated_df
                backup_table.save()
                MessageTableAssociation.objects.create(table=backup_table, message=function_message, operation=MessageTableAssociation.Operation.UPDATE)


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

