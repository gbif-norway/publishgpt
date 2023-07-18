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
    Run python code with access to pandas (pd), numpy (np), and a Django database ORM (db_models) with a 'DataFrame' model and a 'Dataset' model. 
    class Dataset(models.Model):
        created = models.DateTimeField(auto_now_add=True)
        class DWCCore(models.TextChoices):
            EVENT = 'event_occurrences'
            OCCURRENCE = 'occurrence'
            TAXONOMY = 'taxonomy'
        dwc_core = models.CharField(max_length=30, choices=DWCCore.choices, blank=True)
        class DWCExtensions(models.TextChoices):
            SIMPLE_MULTIMEDIA = 'simple_multimedia'
            MEASUREMENT_OR_FACT = 'measurement_or_fact'
            GBIF_RELEVE = 'gbif_releve'
        dwc_extensions = ArrayField(base_field=models.CharField(max_length=500, choices=DWCExtensions.choices), null=True, blank=True)

    class DataFrame(models.Model):
        dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
        df = PickledObjectField()
    
    E.g. you can do `df_obj = db_models.DataFrame.objects.get(id=df_id); print(df_obj.df.to_string());`
    Notes: 
    - Use save() on instances to persist changes or create new objects e.g. `df_obj.save()`
    - Use print() if you want to see output
    - Output is a string of stdout, truncated to 2000 characters
    - Do not include comments in your code
    - NEVER delete objects from the database
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


class PublishDwC(OpenAIBaseModel):
    """To be used as the final step for publishing a dataset which is standardised to Darwin Core"""
    dataset_id: PositiveInt = Field(...)

    @classmethod
    def run():
        pass

