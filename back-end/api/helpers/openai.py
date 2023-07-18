import ast
from api.openai_wrapper import functions
from pydantic import BaseModel


class OpenAIBaseModel(BaseModel):
    @classmethod
    def classname(cls):
        return cls.__name__
    
    @classmethod
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


def callable(function_name):
    return getattr(functions, function_name)


def openai_function_details(response, choice=0):
    message = response['choices'][choice]['message']
    if 'function_call' in message:
        fc = message['function_call']
        return fc['name'], ast.literal_eval(fc['arguments'])

    return None, None


def openai_content(response, choice=0):
    return response['choices'][choice]['message']['content']


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

