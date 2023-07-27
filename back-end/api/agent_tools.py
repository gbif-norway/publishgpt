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
    Run python code with access to pandas (pd), numpy (np), and Django database ORM models `Table` and `Dataset`
    E.g. `df_obj = Table.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Do not edit objects, Use save() on instances to persist changes or create new objects e.g. `df_obj.save()` 
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
        result = ""
        try:
            from api.models import Dataset, Table

            # Make identical duplicate of all the active tables, used for displaying changes to the user but also acts as backups
            duplicates = []
            for t in function_message.agent.dataset.active_tables:
                t.temporary_duplicate_of(t.pk)
                t.pk = None
                t.save()
                duplicates.append(t)

            locals = {}
            globals = { 'Dataset': Dataset, 'Table': Table, 'pd': pd, 'np': np }
            exec(code, globals, locals)
            stdout_value = new_stdout.getvalue()
            
            # Handle table backups
            self.handle_table_backups(function_message, duplicates)

            if stdout_value:
                result = stdout_value
            else:
                result = f"`{code}` executed successfully without errors."
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return f'`{code}` executed, result: {str(result)[:2000]}'

    def handle_table_backups(function_message, duplicates):
        from api.models import Table, FunctionMessageTables

        # Check for newly created tables, and link to message
        for new_table in (function_message.agent.dataset.active_tables - duplicates):
            function_message.function_tables.create(new_table, through_defaults={'operation': FunctionMessageTables.Operation.CREATE})
        
        # Check for deleted tables, soft delete them and link them to the message
        for old_table in (duplicates - function_message.agent.dataset.active_tables):
            old_table.soft_delete()
            function_message.function_tables.create(old_table, through_defaults={'operation': FunctionMessageTables.Operation.DELETE})

        # Check for updated tables which haven't been soft deleted
        for old_table in Table.objects.get(dataset=function_message.agent.dataset, temporary_duplicate_of__isnull=False, deleted_at__isnull=True):
            if not old_table.df.equals(old_table.temporary_duplicate_of.df):
                old_table.temporary_duplicate_of = None
                old_table.stale_at = datetime.now()
                old_table.save()
                function_message.function_tables.create(old_table, through_defaults={'operation': FunctionMessageTables.Operation.UPDATE})
            else:
                old_table.delete()


class SetAgentTaskToComplete(OpenAIBaseModel):
    """Mark an Agent's task as complete"""
    agent_id: PositiveInt = Field(...)

    def run(self):
        from api.models import Agent
        try:
            agent = Agent.objects.get(id=self.agent_id)
            agent.completed = datetime.now()
            agent.save()
            # result = f"Task marked as complete for agent id {self.agent_id} ."
            return None
        except Exception as e:
            return repr(e)[:2000]


class PublishDwC(OpenAIBaseModel):
    """To be used as the final step for publishing a dataset which is standardised to Darwin Core"""
    dataset_id: PositiveInt = Field(...)

    def run(self):
        pass

