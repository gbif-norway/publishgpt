from django.db import models, signals
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from api import df_transformations
import inflection
import pandas as pd
from api.external_apis import openai, openai_fake_functions as fake
import json


class Dataset(models.Model):
    created = models.DateField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=9000, blank=True)
    orcid =  models.CharField(max_length=50, blank=True)
    df_sample = models.JSONField(null=True, blank=True)
    shape = models.JSONField()
    file = models.FileField(upload_to='user_files')
    # dataframe = models.JSONField(null=True, blank=True)

    @property
    def is_published(self):
        False

    @property
    def last_complete_conversation(self):
        return Conversation.objects.filter(dataset=self, complete=True).last()

    @property
    def latest_df_sample(self):
        return self.last_complete_conversation.updated_df_sample

    def get_next_conversation_task(self):
        next = Conversation.objects.filter(dataset=self, status__in=[Conversation.Status.NOT_STARTED, Conversation.Status.NEEDS_USER_INPUT]).first()
        if next:
            print('Next task found:')
            print(next.task.name)
            next.start()
            return next
        return None
    
    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=500)
    initial_user_message = models.CharField(max_length=1500)
    initial_assistant_message = models.CharField(max_length=1500)
    functions = ArrayField(models.CharField(max_length=200))

    def get_available_functions(self):
        return [getattr(fake, f) for f in self.functions]

    class Meta:
        get_latest_by = 'id'
        ordering = ['id']


class Conversation(models.Model):  # 1 conversation per task, multiple conversations per dataset
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    updated_df_sample = models.JSONField(null=True, blank=True)
    class Status(models.TextChoices):
        COMPLETED = 'c'
        SKIPPED = 's'
        NOT_STARTED = 'n'
        NEEDS_USER_INPUT = 'u'
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.NOT_STARTED)

    def get_system_message(self):
        return (
            "You are a human-friendly python code interface working through a series of Tasks in order to get a biodiversity dataframe into darwin core format, ready for publication with gbif.org."
            "The Tasks must be done in a certain order, your current Task is the following: {task}."
            "If the user gets distracted or asks for other things, politely ask them to focus on the current Task, and tell them there will be an opportunity to perform other fixes later."
            "When the user is satisfied, proceed to the next task by calling ProceedToNextTask. "
            "When working with the dataframe, only use the functions you have been provided with. "
            "Full dataframe (loaded from the user's CSV file) has shape: {shape}. "
            "Small sample dataframe: --- {rows} --- "
        ).format(rows=self.dataset.df_sample, shape=self.dataset.shape) 

    def start(self):
        system_message = Message.objects.create(
            conversation=self,
            content=self.get_system_message(),
            role=Message.Role.SYSTEM
        )

        # Make a user message as this seems to be required for the prompt
        instruction_message = Message.objects.create(
            conversation=self,
            content=self.task.system_prompt,
            role=Message.Role.USER
        )
        
        # Store the assistant reply
        response = openai.chat_completion_with_functions(
            messages=[system_message, instruction_message], 
            functions=self.task.get_available_functions()
        )
        response = Message.objects.create(
            conversation=self,
            role=Message.Role.ASSISTANT, 
            gpt_response=response, 
            content=self.task.initial_assistant_message
        )

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    content = models.CharField(max_length=3000, blank=True)
    class Role(models.TextChoices):
        USER = 'user'
        SYSTEM = 'system'
        ASSISTANT = 'assistant'
    role = models.CharField(max_length=10, choices=Role.choices)

    # Assistant message only fields
    gpt_response = models.JSONField(null=True, blank=True)  # Store the full response from the API
    gpt_output_function = models.JSONField(null=True, blank=True)
    df_sample = models.JSONField(null=True, blank=True)

    def clean(self):
        if self.role == Message.Role.ASSISTANT:
            if self.gpt_response is None:
                return ValidationError(_('Assistant messages should have a gpt response'))
    
    def save(self, *args, **kwargs):
        if self.role == Message.Role.ASSISTANT:
            response = self.gpt_response['choices'][0]['message']
            if 'function_call' in response:
                self.gpt_output_function = response['function_call']
                function_name = response['function_call']['name']
                function_args = json.loads(response['function_call']['arguments'])
                print(f'gpt is calling this function {function_name} with args {function_args}')
                if function_name == fake.SetTaskAsComplete.__name__:
                    self.conversation.status = Conversation.Status.COMPLETED
                    self.conversation.save()
                elif function_name == fake.ProceedToNextTask.__name__:
                    self.conversation.status = Conversation.Status.SKIPPED
                    self.conversation.save()
                else:
                    self.conversation.status = Conversation.Status.NEEDS_USER_INPUT
                    rows_df = pd.DataFrame(json.loads(self.conversation.dataset.df_sample), dtype=str)
                    updated_df_sample_df = getattr(df_transformations, inflection.underscore(function_name))(df=rows_df, **function_args)
                    self.conversation.updated_df_sample = updated_df_sample_df.to_json(force_ascii=False)
                    self.df_sample = updated_df_sample_df.to_json(force_ascii=False)
                    self.conversation.save()
            else:
                self.content = response['content']
        super(Message, self).save(*args, **kwargs)

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

# class Publication(models.Model):
#     dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
#     doi = models.CharField(max_length=100)
#     date = models.DateField(null=True)

