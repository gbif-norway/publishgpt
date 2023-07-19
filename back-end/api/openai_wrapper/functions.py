from api import models as db_models
import sys
from io import StringIO
from pydantic import BaseModel, Field, PositiveInt, validate_arguments
import re
import pandas as pd
import numpy as np
from api.helpers.openai import OpenAIBaseModel


class Python(OpenAIBaseModel):
    """
    Run python code with access to pandas (pd), numpy (np), and a Django database ORM (db_models) with a 'DatasetFrame' model and a 'Dataset' model. 
    Dataset fields: created = DateTimeField
    DatasetFrame fields: dataset = ForeignKey to Dataset, title = CharField, df = PickledObjectField, parent = ForeignKey to 'DatasetFrame' with blank=True, null=True
    
    E.g. `df_obj = db_models.DatasetFrame.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: - Use save() on instances to persist changes or create new objects e.g. `df_obj.save()` - Use print() if you want to see output - Output is a string of stdout, truncated to 2000 characters - Do not include comments in your code - Only delete objects from the database if requested by the user
    """
    code: str = Field(..., description="String containing valid python code to be executed in `exec()`")

    def run(self):
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", self.code)
        code = re.sub(r"(\s|`)*$", "", code)
        old_stdout = sys.stdout
        new_stdout = StringIO()
        sys.stdout = new_stdout
        try:
            locals = {}
            globals = { 'db_models': db_models, 'pd': pd, 'np': np }
            exec(code, globals, locals)
            result = new_stdout.getvalue()
        except Exception as e:
            result = repr(e)
        finally:
            sys.stdout = old_stdout
        return str(result)[:2000]


class SetTaskToComplete(OpenAIBaseModel):
    agent_id: PositiveInt = Field(...)
    complete: bool = Field(...)

    def run(self):
        agent = db_models.Agent.objects.get(id=self.agent_id)
        agent.complete = True
        agent.save()


class PublishDwC(OpenAIBaseModel):
    """To be used as the final step for publishing a dataset which is standardised to Darwin Core"""
    dataset_id: PositiveInt = Field(...)

    @classmethod
    def run():
        pass

