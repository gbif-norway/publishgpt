import ast
from pydantic import BaseModel
import json
from openai import OpenAI
from pprint import pprint
from api import agent_tools
from typing import Dict, Any


def create_chat_completion(messages, functions=None, call_first_function=False, temperature=0.8, model='gpt-4o-2024-08-06'): # gpt-3.5-turbo gpt-4o-mini	
    messages = [m.openai_schema for m in messages]
    print('---')
    print(f'---Calling GPT {model} with functions and call_first_function {call_first_function}---')
    args = {'model': model, 'temperature': temperature, 'messages': messages }
    if functions:
        args['tools'] = [{'type': 'function', 'function': f.openai_schema()} for f in functions]
    print('---')
    with OpenAI() as client:
        response = client.chat.completions.create(**args)  
    print('---Response---')
    pprint(response)
    print('---')
    return response

def create_supervisor_chat_completion(messages, functions=None, temperature=1, model='gpt-4o'): # gpt-3.5-turbo gpt-4o-mini	
    messages = [m.openai_schema for m in messages]

def custom_schema(cls: BaseModel) -> Dict[str, Any]:
    parameters = cls.schema()
    parameters['properties'] = {
        k: v
        for k, v in parameters['properties'].items()
        if k not in ('v__duplicate_kwargs', 'args', 'kwargs')
    }
    parameters['required'] = sorted(parameters['properties'])
    for key in ['title', 'additionalProperties', 'description']:
         _remove_a_key(key, 'title')
    return {
        'name': cls.__name__,
        'description': cls.__doc__,
        'parameters': parameters,
    }


class OpenAIBaseModel(BaseModel):
    @classmethod
    def openai_schema(cls):
        return custom_schema(cls)


def load_openai_json_args(json_args, function_name):
    # try:
    return json.loads(json_args, strict=False)  # Throws json.decoder.JSONDecodeError with strict for e.g. """{\n"code": "\nprint('test')"\n}"""
    # except json.decoder.JSONDecodeError:
    #     required = getattr(agent_tools, function_name[0].upper() + function_name[1:]).openai_schema['parameters']['required']
    #     if len(required) == 1:
    #         return {required[0]: json_args}
    #     else:
    #         import pdb; pdb.set_trace()


def get_function(tool):
    # if message.function_call: # Note that function_call is deprecated, see https://platform.openai.com/docs/api-reference/chat/create#chat-create-functions
    #     message.function_call.arguments = load_openai_json_args(message.function_call.arguments, message.function_call.name)
    #     return message.function_call
    # if message.tool_calls:
    # tool = message.tool_calls[0]
    fn = tool.function
    fn.arguments = json.loads(fn.arguments, strict=False) # load_openai_json_args(fn.arguments,fn.name)
    if tool.id:
        fn.id = tool.id
    return fn
    # return None


def openai_message_content(response, choice=0):
    return response['choices'][choice]['message'].get('content')


def _remove_a_key(d, remove_key) -> None:
    """Remove a key from a dictionary recursively"""
    if isinstance(d, dict):
        for key in list(d.keys()):
            if key == remove_key:
                del d[key]
            else:
                _remove_a_key(d[key], remove_key)


def function_name_in_text(function_names, text):
    for string in function_names:
        if string in text:
            return True
    return False

