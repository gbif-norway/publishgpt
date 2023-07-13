from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from api import df_transformations
import pandas as pd
from api.external_apis import openai, callable_functions, prompts
import json
from openai_function_call import openai_function


class Dataset(models.Model):
    created = models.DateField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=2000, blank=True)
    orcid =  models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to='user_files')

    def create_dataframes(self):
        pass

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class DataFrame(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    full = models.JSONField(description='The full dataframe')
    sample = models.JSONField(null=True, blank=True, description='First few and last rows of the dataframe')
    shape = models.JSONField(description='Shape of the dataframe - number of rows and columns')
    description: models.CharField(max_length=2000, blank=True, description='Explains the dataframe content')
    problems: ArrayField(base_field=models.CharField, null=True, blank=True, description='List of holes, inconsistencies and problems in the dataframe')
    derived_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    
    def save_full_df(self, df):
        self.full = df.to_json(force_ascii=False, orient='table')
        self.save()

    @property
    def full_df(self):
        return pd.read_json(self.full, orient='table')
    
    def save_sample_df(self, df):
        self.sample = df.to_json(force_ascii=False, orient='table')
        self.save()
    
    @property
    def sample_df(self):
        return pd.read_json(self.sample, orient='table')
    
    def generate_description_and_problems(self):
        messages = [Message(content=prompts.generate_dataframe_description_and_problems, role=Message.Role.SYSTEM)]
        functions = [callable_functions.run_dataframe_code, callable_functions.DataFrameAnalysis]
        response = openai.chat_completion_with_functions(messages, functions=functions)
        function_called = 
        import pdb; pdb.set_trace()


class Task(models.Model):  
    created = models.DateField(auto_now_add=True)
    task_description = models.CharField(max_length=1000)
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
    conversation = models.ForeignKey(Task, on_delete=models.CASCADE)
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
    df = models.ForeignKey(DataFrame, null=True, blank=True, on_delete=models.SET_NULL)

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


def get_df_sample(df, max_characters=3000):
    # Calculate the target character count per section (top and bottom)
    target_characters_per_section = max_characters // 2
    
    # Convert the DataFrame to a string representation
    df_str = df.to_string(index=False)
    
    # Check if the DataFrame already fits within the character limit
    if len(df_str) <= max_characters:
        return df
    
    # Calculate the reduction factor to scale down the rows
    reduction_factor = target_characters_per_section / 2 / len(df_str)
    
    # Calculate the reduced number of rows
    reduced_n = int(len(df) * reduction_factor)
    
    # Get the top and bottom sections of the DataFrame
    top_df = df.head(reduced_n)
    bottom_df = df.tail(reduced_n)
    
    # Convert the top and bottom sections to string representations
    top_df_str = top_df.to_string(index=False)
    bottom_df_str = bottom_df.to_string(index=False)
    
    # Calculate the remaining available characters
    remaining_characters = max_characters - len(top_df_str) - len(bottom_df_str)
    
    # Calculate the maximum number of rows to fit the remaining characters
    max_rows_to_fit_remaining = remaining_characters // len(df.columns)
    
    # Reduce the number of rows if necessary to fit the remaining characters
    if len(df) > max_rows_to_fit_remaining:
        reduced_n = max_rows_to_fit_remaining
    
    # Get the reduced DataFrame
    reduced_df = df.head(reduced_n)
    
    return reduced_df
