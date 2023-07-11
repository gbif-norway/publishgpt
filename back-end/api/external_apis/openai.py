import openai
# from api.serializers import MessageSerializerForGPT
from pprint import pprint


def serialize_message(message):
    return {'content': message.content, 'role': message.role}

def chat_completion_with_functions(messages, functions, model, function_call='auto'):
    messages = [serialize_message(m) for m in messages]
    gpt_functions = [{'name': x.__name__, 'parameters': x.schema(), 'type': 'object'} for x in functions]

    # function_call = 'auto'
    print('---')
    print(f'---Calling GPT {model} with functions---')
    print(messages)
    print('-')
    pprint(gpt_functions)
    print('---')
    response = openai.ChatCompletion.create(model=model, messages=messages, functions=gpt_functions, temperature=0, function_call=function_call)  
    pprint('---Response---')
    print(response)
    print('---')
    return response

 
def chat_completion(messages, model='gpt-3.5-turbo'):
    messages = [serialize_message(m) for m in messages]
    print('---')
    print('---Calling GPT without functions---')
    print(messages)
    print('---')
    response = openai.ChatCompletion.create(model=model, messages=messages, temperature=0)
    pprint('---Response---')
    print(response)
    print('---')
    return response
