import openai
from pprint import pprint
import json


def create(messages, functions=None, call_first_function=False, temperature=0, model='gpt-4'):
    messages = [m.openai_schema for m in messages]
    print('---')
    print(f'---Calling GPT {model} with functions and call_first_function {call_first_function}---')
    args = {'model': model, 'temperature': temperature, 'messages': messages }
    if functions:
        args['functions'] = [f.openai_schema for f in functions]
        if call_first_function:
            args['function_call'] = {'name': args['functions'][0]['name']}
        else:
            args['function_call'] = 'auto'
    print(args)
    print('---')
    response = openai.ChatCompletion.create(**args)  
    pprint('---Response---')
    print(response)
    print('---')
    return response
