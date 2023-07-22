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
    Run python code with access to pandas (pd), numpy (np), and Django database ORM models `DatasetFrame` and `Dataset`
    E.g. `df_obj = DatasetFrame.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Use save() on instances to persist changes or create new objects e.g. `df_obj.save()` 
    - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters 
    - State does not persist - the slate is wiped clean every time this function is called. 
    """
    code: str = Field(..., description="String containing valid python code to be executed in `exec()`")

    def run(self):
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", self.code)
        code = re.sub(r"(\s|`)*$", "", code)
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        result = ""
        try:
            from api.models import Dataset, DatasetFrame
            locals = {}
            globals = { 'Dataset': Dataset, 'DatasetFrame': DatasetFrame, 'pd': pd, 'np': np }
            exec(code, globals, locals)
            stdout_value = new_stdout.getvalue()

            if stdout_value:
                result = stdout_value
            else:
                result = f"`{code}` executed successfully without errors."
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

