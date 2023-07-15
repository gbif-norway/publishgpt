from openai_function_call import openai_schema
from djantic import ModelSchema


@openai_schema
class Worker(ModelSchema):
    class Config:
        model = db_models.Worker
        include = ['id', 'plan', 'complete']
    

@openai_schema
class DataFrameAnalysis(ModelSchema):
    class Config:
        model = db_models.DataFrame
        include = ['id', 'description', 'problems']