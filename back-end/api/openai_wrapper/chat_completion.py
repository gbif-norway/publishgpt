import openai
from pprint import pprint


def create(messages, functions=None, call_first_function=False, temperature=0, model='gpt-4'):
    messages = [m.openai_schema for m in messages]
    if functions:
        functions = [f.openai_schema for f in functions]
        if call_first_function:
            call = {'name': functions[0]['name']}
        else:
            call = 'auto'

    print('---')
    print(f'---Calling GPT {model} with functions and function_call {call}---')
    if len(messages) > 1:
        print(messages[1:])
    print('-')
    pprint([f['name'] for f in functions])
    print('---')
    response = openai.ChatCompletion.create(model=model, temperature=temperature, messages=messages, functions=functions, function_call=call)  
    pprint('---Response---')
    print(response)
    print('---')
    return response
