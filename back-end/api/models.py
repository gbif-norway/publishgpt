from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
import pandas as pd
from api.openai_wrapper import chat_completion, functions, prompts
from api.helpers.openai import callable, openai_function_details, function_name_in_text
from picklefield.fields import PickledObjectField
import re
import json
import ast


class Worker(models.Model):  
    created = models.DateTimeField(auto_now_add=True)
    task = models.CharField(max_length=9000)
    task_complete = models.BooleanField(null=True, blank=True)
    _functions = ArrayField(base_field=models.CharField(max_length=500))
    _stop_function = models.CharField(max_length=500)

    @property
    def functions(self):
        return [callable(f) for f in self._functions]
    
    @property
    def stop_function(self):
        return callable(self._stop_function)

    @property
    def all_functions(self):
        return self.functions + [self.stop_function]
    
    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

    def run(self, allow_user_feedack=True, current_call=0, max_calls=5):
        if not self.message_set.count():  # Create first message
            Message.objects.create(worker=self, content=self.task, role=Message.Role.SYSTEM)
        
        if current_call == max_calls:
            response = chat_completion.create(self.message_set.all(), [self.stop_function], call_first_function=True)
        else:
            response = chat_completion.create(self.message_set.all(), self.all_functions)
        
        function_name, function_args = openai_function_details(response)
        if function_name:
            function_result = getattr(functions, '_run_python_with_dataframe_orm')(**function_args)
            print(f'Result {function_result}')
            if function_name == self.stop_function.openai_schema['name']:
                print('---STOP FUNCTION--- return None ---')
                # At this point we actually need to return the value if it's not success. I can tell this is a sucky way of doing it. Better would be having it as an API endpoint which it can handle itself
                return None

            Message.objects.create(worker=self, role=Message.Role.FUNCTION, content=function_result, function_name=function_name)
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)

        message = Message.objects.create(worker=self, role=Message.Role.ASSISTANT, content=response['choices'][0]['message']['content'])

        should_have_called_function = function_name_in_text([x['name'] for x in self.all_functions], str(message.content))
        if not allow_user_feedack or should_have_called_function:
            message = Message.objects.create(worker=self, role=Message.Role.USER, content='Please respond with a function call, not text.')
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)

        print('Returned message without function')
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
    created = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    sheet_name = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    problems = ArrayField(base_field=models.CharField(max_length=500), null=True, blank=True)


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
