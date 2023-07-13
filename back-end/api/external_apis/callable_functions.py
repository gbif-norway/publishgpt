from pydantic import BaseModel, Field, PositiveInt, decorator
from typing import List
from typing_extensions import Annotated
from enum import Enum
from openai_function_call import openai_function, openai_schema
import pandas as pd
from api import models as db_models
from djantic import ModelSchema
from marvin import ai_fn, ai_model


@openai_function
def run_dataframe_code(df_id: int, code: str) -> str:
    """
    Run any python or pandas `code` on a single dataframe named `df`, which was loaded with dtype="str"
    e.g. 1: get a subset of the first 5 rows x 5 columns - `return df.iloc[:5, :5]`
    e.g. 2: attempt to get the sum of column 4, excluding a possible header row - `col_4 = df.iloc[1:, 4].astype(float); return col_4.sum(), col_4.mean(), col_4.std()`
    Note: Return is a string limited to 2000 characters. If an error is found in the python code, that error will be returned.
    """
    try:
        df = db_models.DataFrame.objects.get(df_id).full_df
        print(code)
        result = exec(code)
        df.regenerate_sample()
    except Exception as e:
        result = e
    return str(result)[:2000]


@openai_function
def run_dataframes_code(df_ids: List[int], code: str) -> str:
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
            df_obj.save_full_df(df)
        result = exec(code)
    except Exception as e:
        result = e
    return str(result)[:2000]


@openai_schema
class DataFrameAnalysis(ModelSchema):
    class Config:
        model = db_models.DataFrame
        include = ['id', 'sample', 'shape', 'description', 'problems']
