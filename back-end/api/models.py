from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api import agent_tools
from api.helpers.openai_helpers import openai_function_details, function_name_in_text, create_chat_completion
from picklefield.fields import PickledObjectField
import pandas as pd
from datetime import datetime
from django.template.loader import render_to_string
from os import path
from django.db.models import Count, Max
from pydantic import ValidationError


class Dataset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    orcid =  models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to='user_files')

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

    @property
    def filename(self):
        return path.basename(self.file.name)
    
    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=300, unique=True)
    text = models.CharField(max_length=5000)
    per_table = models.BooleanField()

    class Meta:
        get_latest_by = 'id'
        ordering = ['id']

    @property
    def functions(self):
        return [agent_tools.Python.__name__, agent_tools.SetAgentTaskToComplete.__name__]

    def create_agents_with_system_messages(self, dataset:Dataset):
        active_tables = Table.objects.filter(dataset=dataset, deleted=None)
        agents = []
        if self.per_table:  # One agent per table
            for dataset_frame in active_tables:
                agent = Agent.create_with_system_message(dataset=dataset, task=self, dataset_frames=[dataset_frame])
                agents.append(agent)
        else:  # One agent for all the tables
            agent = Agent.create_with_system_message(dataset=dataset, task=self, dataset_frames=active_tables)
            agents.append(agent)

        return agents


class Agent(models.Model):  
    created = models.DateTimeField(auto_now_add=True)
    completed = models.DateTimeField(null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    @property
    def callable_functions(self):
        return [getattr(agent_tools, f) for f in self.task.functions]

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

    def get_next_assistant_message_for_user(self):
        if self.completed:
            return None
        
        last_message = self.message_set.last()
        if last_message.role == Message.Role.ASSISTANT:
            return last_message
        
        return self.run(allow_user_feedack=True)

    @classmethod
    def create_with_system_message(cls, dataset_frames, **kwargs):
        agent = cls.objects.create(**kwargs)
        system_message_text = render_to_string('prompt.txt', context={ 'agent': agent, 'task_text': agent.task.text, 'agent_tables': dataset_frames, 'all_tasks_count': Task.objects.all().count() })
        print(system_message_text)
        Message.objects.create(agent=agent, content=system_message_text, role=Message.Role.SYSTEM)
        return agent

    def run(self, allow_user_feedack=True, current_call=0, max_calls=10):
        response = create_chat_completion(self.message_set.all(), self.callable_functions, call_first_function=(current_call == max_calls))
        
        # Run a function if GPT has asked for a function to be called
        function_name, function_args = openai_function_details(response)
        message_content = response['choices'][0]['message'].get('content')
        print(f'Response message content: {message_content}')
        if function_name:
            # Sometimes GPT sends back message content as well as a function call, if it does then let's store it and show it to the user
            if message_content:
                Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=message_content, display_to_user=True)
                print(f'GPT function reply content message: {message_content}')
            function_model_class = getattr(agent_tools, function_name)
            
            print(f'FUNCTION ARGS: {function_args}')
            function_model_obj = function_model_class(**function_args)  # I think pydantic validation is called here automatically when we instantiate
            function_result = function_model_obj.run()

            Message.objects.create(agent=self, role=Message.Role.FUNCTION, content=function_result, function_name=function_name)
            # TODO Get all Tables which are not linked to a message and are linked to this dataset, and link them to the 
            print(f'FUNCTION RESULT: {function_result}')
            
            # If there is a function result, we need to feed it back to GPT4, otherwise it has set the agent to be complete
            if function_result:
                return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)
            return None  # If an agent is set to complete

        # If GPT didn't call the function properly or if we don't want user feedback, ask it to call a function
        if not allow_user_feedack or function_name_in_text(self.task.functions, message_content):
            message = Message.objects.create(agent=self, role=Message.Role.USER, content='Please respond with a function call, not text.')
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)

        # Store GPT's message
        message = Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=message_content, display_to_user=True)
        return message


class Table(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    problems = ArrayField(base_field=models.CharField(max_length=500), null=True, blank=True)
    # parent = models.ForeignKey('Table', on_delete=models.CASCADE, blank=True, null=True)
    deleted = models.DateTimeField(null=True, blank=True)  # Is null if the dataset is not deleted

    @property
    def df_json(self):
        return self.df.to_json(orient='records', date_format='iso')

    def soft_delete(self):
        self.deleted = datetime.now()
        self.save()
    
    def _snapshot_df(self):
        max_rows, max_columns, max_str_len = 5, 5, 70

        # Truncate long strings in cells
        df = self.df.astype(str).applymap(lambda x: (x[:max_str_len - 3] + '...') if len(x) > max_str_len else x)

        # Truncate rows
        if len(df) > max_rows:
            top = df.head(max_rows // 2)
            bottom = df.tail(max_rows // 2)
            df = pd.concat([top, pd.DataFrame({col: ['...'] for col in df.columns}, index=['...']), bottom])

        # Truncate columns
        if len(df.columns) > max_columns:
            left = df.iloc[:, :max_columns//2]
            right = df.iloc[:, -max_columns//2:]
            middle = pd.DataFrame({ '...': ['...']*len(df) }, index=df.index)
            df = pd.concat([left, middle, right], axis=1)
        
        return df.fillna('')

    # def __str__(self):
    #     original_rows, original_cols = self.df.shape
    #     return self._snapshot_df().to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

    @property
    def str_snapshot(self):
        original_rows, original_cols = self.df.shape
        return self._snapshot_df().to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

    @property
    def html_snapshot(self):
        original_rows, original_cols = self.df.shape
        return self._snapshot_df().to_html() + f"\n\nTitle {self.title}: [{original_rows} rows x {original_cols} columns]"


class Message(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=9000, blank=True)
    function_name = models.CharField(max_length=200, blank=True)  # Only for function role messages
    display_to_user = models.BooleanField(default=False)
    dataset_frames = models.ManyToManyField(Table, blank=True)

    class Role(models.TextChoices):
        USER = 'user'
        SYSTEM = 'system'
        ASSISTANT = 'assistant'
        FUNCTION = 'function'
    role = models.CharField(max_length=10, choices=Role.choices)

    @property
    def openai_schema(self):
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
