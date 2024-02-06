import ast
from pydantic import BaseModel
from pydantic.main import ModelMetaclass
import json
import openai
from pprint import pprint
from api import agent_tools


def create_chat_completion(messages, functions=None, call_first_function=False, temperature=1, model='gpt-4-turbo-preview'): # gpt-3.5-turbo
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
    print('---')
    response = openai.ChatCompletion.create(**args)  
    print('---Response---')
    pprint(response)
    print('---')
    return response


class OpenAIBaseMeta(ModelMetaclass):
    @property
    def openai_schema(cls):
        parameters = cls.schema()  # Note this is a class method inherited from BaseModel
        parameters['properties'] = {
            k: v
            for k, v in parameters['properties'].items()
            if k not in ('v__duplicate_kwargs', 'args', 'kwargs')
        }
        parameters['required'] = sorted(parameters['properties'])
        _remove_a_key(parameters, 'title')
        _remove_a_key(parameters, 'additionalProperties')
        _remove_a_key(parameters, 'description')
        return {
            'name': cls.__name__,
            'description': cls.__doc__,
            'parameters': parameters,
        }

class OpenAIBaseModel(BaseModel, metaclass=OpenAIBaseMeta):
    pass


def check_function_args(response, choice=0):
    message = response.choices[choice].message
    args = {}
    if message.tool_calls:
        fc = message.tool_calls[0]
        try:
            args = ast.literal_eval(fc.function.arguments)
        except (SyntaxError, ValueError):
            try:
                args = json.loads(fc.function.arguments, strict=False)  # Throws json.decoder.JSONDecodeError with strict for e.g. """{\n"code": "\nprint('test')"\n}"""
            except json.decoder.JSONDecodeError:
                required = getattr(agent_tools, fc.function.name).openai_schema['parameters']['required']
                if len(required) == 1:
                    args = {required[0]: fc.function.arguments}
                else:
                    import pdb; pdb.set_trace()
        except:
            import pdb; pdb.set_trace()

        fc.function.arguments = args
        return fc

    return None


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

