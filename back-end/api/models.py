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
        next = Conversation.objects.filter(dataset=self, status__in=[Conversation.Status.NOT_STARTED, Conversation.Status.IN_PROGRESS]).first()
        if next:
            print('Next task found:')
            print(next.task.name)
            next.start()
            print(f'Starting the task has finished, status is {next.status}')
            if next.status in [Conversation.Status.NOT_STARTED, Conversation.Status.IN_PROGRESS]:
                return next
            self.get_next_conversation_task()
        return None
    
    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=500)
    initial_user_message = models.CharField(max_length=1500)
    initial_assistant_message = models.CharField(max_length=1500)
    initial_function = models.CharField(max_length=200)
    functions = ArrayField(models.CharField(max_length=200))
    class GPTModel(models.TextChoices):
        GPT_35 = 'gpt-3.5-turbo'
        GPT_35_16K = 'gpt-3.5-turbo-16k'
        GPT_4 = 'gpt-4'
    gpt_model = models.CharField(max_length=30, choices=GPTModel.choices, default=GPTModel.GPT_35_16K)

    @property
    def function_objects(self):
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
        COMPLETED = 'completed'
        SKIPPED = 'skipped'
        NOT_STARTED = 'not_started'
        IN_PROGRESS = 'in_progress'
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)

    def get_system_message(self):
        return (
            "You are a human-friendly python code interface working through a series of Tasks in order to get a biodiversity dataframe into darwin core format, ready for publication with gbif.org. "
            "The Tasks must be done in a certain order, your current Task is the following: {task}. "
            "When working with the dataframe, only use the functions you have been provided with. "
            "Full dataframe (loaded from the user's CSV file) has shape: {shape}. "
            "Small sample dataframe: --- {rows} --- "
        ).format(rows=self.dataset.df_sample, shape=self.dataset.shape, task=self.task.description) 

    def start(self):
        system_message = Message.objects.create(
            conversation=self,
            content=self.get_system_message(),
            role=Message.Role.SYSTEM
        )

        # Make a user message as this seems to be required for the prompt
        instruction_message = Message(
            conversation=self,
            content=self.task.initial_user_message,
            role=Message.Role.USER
        )
        
        # Store the assistant reply
        function = getattr(fake, self.task.initial_function)
        gpt_response = openai.chat_completion_with_functions(
            messages=[system_message, instruction_message], 
            functions=[function],
            function_call={'name': function.__name__},
            model=self.task.gpt_model
        )
        assistant_message = Message.objects.create(
            conversation=self,
            role=Message.Role.ASSISTANT, 
            gpt_response=gpt_response, 
            content=self.task.initial_assistant_message
        )

        # Edit the system message so it knows to only move onto the ProceedToNextTask if the real user is satisfied
        system_message.content += (
            "If the user gets distracted or asks for other things, politely ask them to focus on the current Task, and tell them there will be an opportunity to perform other fixes later."
            "When the user is satisfied, call GoToNextTask with set_current_task_status='completed'. If the user wishes to skip the task, call GoToNextTask with set_current_task_status='skipped'."
        )
        system_message.save()

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
                stops = Task.objects.values_list('initial_function', flat=True)
                if function_name in [getattr(fake, x).__name__ for x in stops] + [fake.GoToNextTask.__name__]: 
                    self.conversation.status = function_args['set_current_task_status']
                    self.conversation.save()
                else:
                    # Prompt the user to allow us to proceed to the next task
                    self.content = 'Does this look ok?' 
                    if self.conversation.status == Conversation.Status.NOT_STARTED:
                        self.content = self.conversation.task.initial_assistant_message

                    # Run the desired function over the sample, ready to display to the user
                    rows_df = pd.DataFrame(json.loads(self.conversation.dataset.df_sample), dtype=str)
                    updated_df_sample_df = getattr(df_transformations, inflection.underscore(function_name))(df=rows_df, **function_args)
                    self.df_sample = updated_df_sample_df.to_json(force_ascii=False)
                    self.conversation.updated_df_sample = updated_df_sample_df.to_json(force_ascii=False)
                    self.conversation.status = Conversation.Status.IN_PROGRESS
                    self.conversation.save()
            else:
                print('No function call from gpt')
                self.content = response['content']
        super(Message, self).save(*args, **kwargs)

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

# class Publication(models.Model):
#     dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
#     doi = models.CharField(max_length=100)
#     date = models.DateField(null=True)

