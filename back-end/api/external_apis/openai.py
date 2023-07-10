import openai
# from api.serializers import MessageSerializerForGPT
from rest_framework import serializers
from pprint import pprint


MODEL = 'gpt-3.5-turbo-16k'

def serialize_message(message):
    return {'content': message.content, 'role': message.role}

def chat_completion_with_functions(messages, functions):
    # messages = [MessageSerializerForGPT(m).data for m in messages]
    messages = [serialize_message(m) for m in messages]
    gpt_functions = [{'name': x.__name__, 'parameters': x.schema(), 'type': 'object'} for x in functions]

    # function_call = 'auto'
    
    print('---')
    print('---Calling GPT with functions---')
    print(messages)
    print('-')
    pprint(gpt_functions)
    print('---')
    response = openai.ChatCompletion.create(model=MODEL, messages=messages, functions=gpt_functions, temperature=0)  
    pprint('response')
    print(response)
    print('---')
    return response

 
def chat_completion(messages):
    messages = [serialize_message(m) for m in messages]
    # messages = [MessageSerializerForGPT(m).data for m in messages]
    return openai.ChatCompletion.create(model=MODEL, messages=messages)
