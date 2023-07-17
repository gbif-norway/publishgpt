from typing import List
from openai_function_call import openai_function
from api import models as db_models
from api import helpers
from django.db import transaction
from enum import Enum
import sys
from io import StringIO
from pydantic import BaseModel, Field, PositiveInt
from rest_framework import serializers
import re
import pandas as pd

@openai_function
def run_python_with_dataframe_orm(code: str):
    """
    Run valid python code with access to pandas (pd) and a Django database ORM with a 'DataFrame' model and a 'Dataset' model. 
    class Dataset(models.Model):
        created = models.DateTimeField(auto_now_add=True)
    class DataFrame(models.Model):
        dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
        df = PickledObjectField()
    E.g. you can do `df_obj = db_models.DataFrame.objects.get(id=df_id); print(df_obj.df.to_string());`
    You also can persist changes to the database by calling .save() on DataFrame instances
    If you want to see the output of something, print it out. 
    Keep in mind that results will be truncated at 2000 characters.
    Do not include code comments.
    """
    pass

def _run_python_with_dataframe_orm(code: str):
    """
    Run valid python code with access to pandas (pd) and a Django database ORM with a 'DataFrame' model and a 'Dataset' model. 
    class Dataset(models.Model):
        created = models.DateTimeField(auto_now_add=True)
    class DataFrame(models.Model):
        dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
        df = PickledObjectField()
    E.g. you can do `df_obj = db_models.DataFrame.objects.get(id=df_id); print(df_obj.df.to_string());`
    You also can persist changes to the database by calling .save() on DataFrame instances
    If you want to see the output of something, print it out. 
    Keep in mind that results will be truncated at 2000 characters.
    Do not include code comments.
    """
    print(f"RUNNING run_python_with_dataframe_orm with {code}")
    old_stdout = sys.stdout
    new_stdout = StringIO()
    sys.stdout = new_stdout
    code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", code)
    code = re.sub(r"(\s|`)*$", "", code)
    try:
        locals = {}
        globals = { 'db_models': db_models, 'pd': pd }
        exec(code, globals, locals)
        result = new_stdout.getvalue()
    except Exception as e:
        result = repr(e)
    finally:
        sys.stdout = old_stdout
    return str(result)[:2000]

@openai_function
def publish_dwc(dataset_id: int):
    """To be used as the final step for publishing a dataset which is standardised to Darwin Core"""
    pass

@openai_function
def adjust_plan(worker_id: int):
    """To be used by a worker to adjust its own plan"""
    pass


class PlanItem(BaseModel):
    df_ids: List[int] = Field(...)
    plan_step: str = Field(...)
    plan_title: str = Field(...)

@openai_function
def save_dataset_plan(dataset_id: int, plan: List[PlanItem]):
    """Save a plan for a dataset"""
    try:
        dataset = db_models.Dataset.objects.get(id=dataset_id)
        plan_items = []
        for p in plan:
            plan_items.append({'df_ids': p.df_ids, 'plan_step': p.plan_step, 'plan_title': p.plan_title})
        import pdb; pdb.set_trace()
        dataset.plan = plan_items
        dataset.save()
        return 'Success'
    except Exception as e:
        result = e
    return result


class CoreTypeEnum(str, Enum):
    EVENT = 'event_occurrences'
    OCCURRENCE = 'occurrence'
    TAXONOMY = 'taxonomy'

class ExtensionTypeEnum(str, Enum):
    SIMPLE_MULTIMEDIA = 'simple_multimedia'
    MEASUREMENT_OR_FACT = 'measurement_or_fact'
    GBIF_RELEVE = 'gbif_releve'

@openai_function
def allocate_dataset_core_and_extensions(dataset_id: int, dwc_core: CoreTypeEnum, dwc_extensions: List[ExtensionTypeEnum] = []):
    """
    Save the core choice and any extensions
    """
    try:
        dataset = db_models.Dataset.objects.get(id=dataset_id)
        dataset.dwc_core = dwc_core
        dataset.dwc_extensions = dwc_extensions
        dataset.save()
        result = f'Successfully allocated core and extension to {dataset_id}'
    except Exception as e:
        result = e
    return result


@openai_function
def save_description_and_problems(df_id: int, description: str, problems: List[str]):
    """
    Save a description of the contents of a dataframe, and a list of problems identified
    """
    try:
        with transaction.atomic():
            df = db_models.DataFrame.objects.get(id=df_id)
            df.description = description
            df.problems = problems
            df.save()
        result = f'Successfully saved {df.id}'
    except Exception as e:
        result = e
    return result


@openai_function
def set_task_status_to_complete(worker_id: int):
    """
    Registers a task as being completed
    """
    worker = db_models.Worker.objects.get(id=worker_id)
    worker.task_complete = True
    worker.save()
    return worker


@openai_function
def query_dataframe(df_id: int, code: str) -> str:
    """
    Run any python or pandas `code` to query a single dataframe named `df` which has been loaded from the database: `df = db_models.DataFrame.objects.get(df_id)`
    e.g. 1: get a subset of the first 5 rows x 5 columns - `return df.iloc[:5, :5]`
    e.g. 2: attempt to get the sum of column 4, excluding a possible header row - `col_4 = df.iloc[1:, 4].astype(float); return col_4.sum(), col_4.mean(), col_4.std()`
    
    Note 1: Return is a string limited to 2000 characters. *ALWAYS* include a 'return'
    Note 2: If an error is found in the python code, that error will be returned.
    Note 3: Changes to the dataframe are not persisted
    """
    try:
        dataframe = db_models.DataFrame.objects.get(id=df_id)
        print(f'Code: `{code}`')
        locals = {'df': dataframe.df}
        globals = {}
        exec(f'def temp_func(df):\n\t{code}', globals, locals)
        temp_func = locals['temp_func']
        # import pdb; pdb.set_trace()
        result = temp_func(dataframe.df)
    except Exception as e:
        print(f'EXCEPTION {e}')
        result = e
    return str(result)[:2000]


@openai_function
def edit_dataframe(df_id: int, code: str) -> str:
    """
    Run any python or pandas `code` on a single dataframe named `df`, which was loaded with dtype="str"
    Notes: Return is a string limited to 2000 characters. Changes to df are saved after your code, using df.save(), any error messages will be returned, otherwise the first 2000 characters of the dataframe will be returned.
    """
    try:
        dataframe = db_models.DataFrame.objects.get(df_id)
        print(code)
        locals = {'df': dataframe.df}
        exec(code, {}, locals)
        dataframe.df = locals['df']
        dataframe.save()
        result = dataframe.df.to_string()
    except Exception as e:
        result = e
    return str(result)[:2000]




@openai_function
def create_dataframe_from_existing_dataframes(df_ids: List[int], code: str) -> int:
    """
    Run any python or pandas `code` to create a dataframe. 
    You have access to a dictionary of pandas DataFrames named `dfs`, with the keys being the df_ids, and the values being the pandas Dataframes
    dataframe named `df`, which was loaded with dtype="str"
    Notes: Return is an int string limited to 2000 characters. Changes to df are saved after your code, using dataframe.save(), any error messages will be returned, otherwise the first 2000 characters of the dataframe will be returned.
    """
    try:
        dataframe = db_models.DataFrame.objects.get(df_id)
        print(code)
        locals = {'df': dataframe.df}
        exec(code, {}, locals)
        dataframe.df = locals['df']
        dataframe.save()
        result = dataframe.df.to_string()
    except Exception as e:
        result = e
    return str(result)[:2000]


@openai_function
def run_code_on_multiple_dataframes(df_ids: List[int], code: str) -> str:
    """
    Run any python or pandas `code` on multiple dataframes. 
    You have access to a dictionary of pandas DataFrames named `dfs`, with the keys being the df_ids, and the values being the pandas Dataframes
    I.e. dfs = {df.pk: df.full_df for df in db_models.DataFrame.objects.filter(id__in=df_ids)} is run before your code
    Each dataframe in the dictionary will be saved after your code is run. 
    Note: Return is a string limited to 2000 characters. If an error is found in the python code, that error will be returned.
    """
    try:
        dfs = {df.pk: df.full_df for df in db_models.DataFrame.objects.filter(id__in=df_ids)}
        import pdb; pdb.set_trace()
        for pk, df in dfs.items():
            df_obj = db_models.DataFrame.objects.get(pk=pk)
        result = exec(code)
    except Exception as e:
        result = e
    return str(result)[:2000]

