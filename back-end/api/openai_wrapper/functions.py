from typing import List
from openai_function_call import openai_function
from api import models as db_models
from api import helpers
from django.db import transaction


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
    Notes: Return is a string limited to 2000 characters. Changes to df are saved after your code, using dataframe.save(), any error messages will be returned, otherwise the first 2000 characters of the dataframe will be returned.
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

