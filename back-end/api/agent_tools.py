import sys
from io import StringIO
from pydantic import Field, PositiveInt
import re
import pandas as pd
import numpy as np
from api.helpers.openai_helpers import OpenAIBaseModel
from datetime import datetime


class Python(OpenAIBaseModel):
    """
    Run python code using `exec(code, globals={'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np}, {})`, i.e. with access to pandas (pd), numpy (np), and Django database ORM models `Table` and `Dataset`
    E.g. `df_obj = Table.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Edit, delete or create new Table objects as required - remember to save changes to the database (e.g. `df_obj.save()`). A backup of all Table objects is made before running your code.
    - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters 
    - State does not persist - the slate is wiped clean every time this function is called. 
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
                result = f"`{code}` executed successfully without errors."
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
        for old_table in duplicates.filter(temporary_duplicate_of=None):
            old_table.soft_delete()
            MessageTableAssociation.objects.create(table=old_table, message=function_message, operation=MessageTableAssociation.Operation.DELETE)

        # Check for newly created tables, and link to message
        for new_table in [t for t in new_tables if t.id not in duplicates.values_list('temporary_duplicate_of__id', flat=True)]:
            MessageTableAssociation.objects.create(table=new_table, message=function_message, operation=MessageTableAssociation.Operation.CREATE)
        
        # Check for updated tables which haven't been soft deleted
        remaining_tables = duplicates.exclude(temporary_duplicate_of=None)
        for old_table in remaining_tables:
            new_table = old_table.temporary_duplicate_of
            if not old_table.df.equals(new_table.df):
                old_table.temporary_duplicate_of = None  # Hmm... do we want to actually keep track of which table inherits from which?
                old_table.stale_at = datetime.now()
                old_table.save()
                # MessageTableAssociation.objects.create(table=old_table, message=function_message, operation=MessageTableAssociation.Operation.UPDATE)
                MessageTableAssociation.objects.create(table=new_table, message=function_message, operation=MessageTableAssociation.Operation.UPDATE)
            else:
                old_table.delete()


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

