from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
import pandas as pd
from api.openai_wrapper import chat_completion, functions, prompts
from api import helpers
from picklefield.fields import PickledObjectField
import re
import json
import ast


class Function(models.Model):
    name = models.CharField(max_length=500, primary_key=True)

    @property
    def openai_schema(self):
        return self.callable_object.openai_schema
    
    @property
    def callable_object(self):
        return getattr(functions, self.name)


class Worker(models.Model):  
    created = models.DateTimeField(auto_now_add=True)
    task = models.CharField(max_length=9000)
    task_complete = models.BooleanField(null=True, blank=True)
    functions = models.ManyToManyField(Function)
    stop_function = models.ForeignKey(Function, on_delete=models.CASCADE, related_name='stop_functions')

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

    def run(self, allow_user_feedack=True, current_call=0, max_calls=5):
        if not self.message_set.count():  # Create first message
            Message.objects.create(worker=self, content=self.task, role=Message.Role.SYSTEM)
        
        print(f'Call {current_call} for worker {self.pk}')
        all_functions = [self.stop_function] + list(self.functions.all())
        if current_call == max_calls:
            response = chat_completion.create(self.message_set.all(), [self.stop_function], call_first_function=True)
        else:
            response = chat_completion.create(self.message_set.all(), all_functions)
        
        response_message = response['choices'][0]['message']

        if 'function_call' in response_message:
            name = response_message['function_call']['name']
            print(f'Calling {name}')
            if name != 'run_python_with_dataframe_orm':
                function_result = Function.objects.get(name=name).callable_object.from_response(response)
            else:
                try:
                    code_arg = ast.literal_eval(response_message['function_call']['arguments'])['code']
                    print(f'got code arg {code_arg}')
                    function_result = getattr(functions, '_run_python_with_dataframe_orm')(code=code_arg)
                    print(f'got function result {function_result}')
                except:
                    import pdb; pdb.set_trace()
            print(f'Result {function_result}')
            if function_result is None: # or function_result == 'None':
                import pdb; pdb.set_trace()
            if name == self.stop_function.openai_schema['name']:
                print('---STOP FUNCTION--- return None ---')
                # At this point we actually need to return the value if it's not success. I can tell this is a sucky way of doing it. Better would be having it as an API endpoint which it can handle itself
                return None

            Message.objects.create(worker=self, role=Message.Role.FUNCTION, content=function_result, function_name=name)
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)
        import pdb; pdb.set_trace()
        message = Message.objects.create(worker=self, role=Message.Role.ASSISTANT, content=response_message['content'])

        should_have_called_function = helpers.function_name_in_text([f.openai_schema['name'] for f in all_functions], str(message.content))
        if not allow_user_feedack or should_have_called_function:
            message = Message.objects.create(worker=self, role=Message.Role.USER, content='Please respond with a function call, not text.')
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)

        print('Returned message without function')
        # import pdb; pdb.set_trace()
        return message


class Dataset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    orcid =  models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to='user_files')
    master_worker = models.ForeignKey(Worker, on_delete=models.CASCADE, null=True, blank=True)
    plan = models.JSONField(null=True, blank=True)

    class DWCCore(models.TextChoices):
        EVENT = 'event_occurrences'
        OCCURRENCE = 'occurrence'
        TAXONOMY = 'taxonomy'
    dwc_core = models.CharField(max_length=30, choices=DWCCore.choices, blank=True)

    class DWCExtensions(models.TextChoices):
        SIMPLE_MULTIMEDIA = 'simple_multimedia'
        MEASUREMENT_OR_FACT = 'measurement_or_fact'
        GBIF_RELEVE = 'gbif_releve'
    dwc_extensions = ArrayField(base_field=models.CharField(max_length=500, choices=DWCExtensions.choices), null=True, blank=True)

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class DataFrame(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    sheet_name = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    problems = ArrayField(base_field=models.CharField(max_length=500), null=True, blank=True)

    def _prompt_args(self):
        return {'id': self.id, 
                'sheet_name': self.sheet_name,
                'snapshot': helpers.trunc_df_to_string(self.df)}

    def get_summary_str(self):
        prompt_args = self._prompt_args() | { 'description': self.description, 'problems': self.problems }
        return prompts.dataframe_summary.format(**prompt_args)
    
    def generate_description_and_problems(self):
        print(f'GENERATING FOR {self.sheet_name}')
        worker = Worker.objects.create(
            task=prompts.generate_dataframe_description_and_problems.format(**self._prompt_args()),
            stop_function=Function.objects.get(pk=functions.save_description_and_problems.openai_schema['name'])
        )
        worker.functions.add(functions.query_dataframe.openai_schema['name'])
        worker.run(allow_user_feedack=False)


class Message(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=9000, blank=True)
    function_name = models.CharField(max_length=200, blank=True)  # Only for function role messages

    class Role(models.TextChoices):
        USER = 'user'
        SYSTEM = 'system'
        ASSISTANT = 'assistant'
        FUNCTION = 'function'
    role = models.CharField(max_length=10, choices=Role.choices)

    @property
    def openai_schema(self):
        print(f'------{self.role}: {self.content[:100]}---')
        # import pdb; pdb.set_trace()
        if self.role == Message.Role.FUNCTION:
            return { 'content': self.content, 'role': self.role, 'name': self.function_name }
        return { 'content': self.content, 'role': self.role }

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class Metadata(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=2000, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
