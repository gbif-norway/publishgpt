from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api import agent_tools
from api.helpers.openai_helpers import get_function, create_chat_completion
from picklefield.fields import PickledObjectField
import pandas as pd
from django.template.loader import render_to_string
from os import path
import json
from pydantic_core._pydantic_core import ValidationError


class Dataset(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    orcid = models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to='user_files')
    title = models.CharField(max_length=500, blank=True, default='')
    structure_notes = models.CharField(max_length=2000, blank=True, default='')
    description = models.CharField(max_length=2000, blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    dwca_url = models.CharField(max_length=50, blank=True)
    user_language = models.CharField(max_length=100, blank=True)

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
    
    def next_agent(self):
        self.refresh_from_db()
        if self.rejected_at:
            print('rejected')
            return None
        
        next_agent = self.agent_set.filter(completed_at=None).first()
        if next_agent:
            return next_agent
    
        last_completed_agent = self.agent_set.last()  # self.agent_set.exclude(completed_at=None).last() 
        print(f'No next agent found, making new agent for new task based on {last_completed_agent}')
        if last_completed_agent:
            next_task = Task.objects.filter(id__gt=last_completed_agent.task.id).first()
            if next_task:
                next_task.create_agents_with_system_messages(dataset=self)
                return self.next_agent()
            else:
                print(f'PUBLISHED {self.published_at}')
                return None  # It's been published... self.published_at = datetime.now() # self.save()
        else:
            raise Exception('Agent set for this dataset appears to be empty')

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=300, unique=True)
    text = models.TextField()
    per_table = models.BooleanField()
    attempt_autonomous = models.BooleanField()
    additional_function = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        get_latest_by = 'id'
        ordering = ['id']

    @property
    def functions(self):
        functions = [agent_tools.Python.__name__, agent_tools.SetAgentTaskToComplete.__name__]
        if self.additional_function:
            functions.append(self.additional_function)
        return functions

    def create_agents_with_system_messages(self, dataset:Dataset):
        tables = Table.objects.filter(dataset=dataset)
        agents = []
        if self.per_table:  # One agent per table
            for table in tables:
                agent = Agent.create_with_system_message(dataset=dataset, task=self, tables=[table])
                agents.append(agent)
        else:  # One agent for all the tables
            agent = Agent.create_with_system_message(dataset=dataset, task=self, tables=tables)
            agents.append(agent)

        return agents


class Table(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)

    @property
    def df_json(self):
        df = self.make_columns_unique(self.df)
        return df.to_json(orient='records', date_format='iso')

    def _snapshot_df(self, df_obj):
        max_rows, max_columns, max_str_len = 10, 10, 70

        # Truncate long strings in cells
        df = df_obj.apply(lambda col: col.astype(str).map(lambda x: (x[:max_str_len - 3] + '...') if len(x) > max_str_len else x))

        # Truncate columns
        if len(df.columns) > max_columns:
            left = df.iloc[:, :max_columns//2]
            right = df.iloc[:, -max_columns//2:]
            middle = pd.DataFrame({ '...': ['...']*len(df) }, index=df.index)
            df = pd.concat([left, middle, right], axis=1)
        
        df.fillna('', inplace=True)

        # Truncate rows
        if len(df) > max_rows:
            top = df.head(max_rows // 2)
            bottom = df.tail(max_rows // 2)
            middle = pd.DataFrame({col: ['...'] for col in df.columns}, index=[0])  # Use a temporary numeric index for middle
            df = pd.concat([top, middle, bottom], ignore_index=True)
            # df = '\n'.join([top, middle, bottom])

        return df

    @property
    def str_snapshot(self):
        df = self.make_columns_unique(self.df)
        original_rows, original_cols = self.df.shape
        return self._snapshot_df(df).to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

    def make_columns_unique(self, df):
        cols = pd.Series(df.columns)
        nan_count = 0
        for i, col in enumerate(cols):
            if pd.isna(col):
                nan_count += 1
                cols[i] = f"NaN ({nan_count})"
            elif (cols == col).sum() > 1:
                dup_indices = cols[cols == col].index
                for j, idx in enumerate(dup_indices, start=1):
                    if j > 1:
                        cols[idx] = f"{col} ({j})"
        
        df.columns = cols
        return df


class Agent(models.Model):  
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    tables = models.ManyToManyField(Table, blank=True)
    busy_thinking = models.BooleanField(default=False)

    @property
    def callable_functions(self):
        return [getattr(agent_tools, f) for f in self.task.functions]

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']

    @classmethod
    def create_with_system_message(cls, dataset, task, tables):
        agent = cls.objects.create(dataset=dataset, task=task)
        agent.tables.set([t.id for t in tables])
        system_message_text = render_to_string('prompt.txt', context={ 'agent': agent, 'task_text': agent.task.text, 'agent_tables': tables, 'all_tasks_count': Task.objects.all().count(), 'task_autonomous': agent.task.attempt_autonomous,  })
        print(system_message_text)
        Message.objects.create(agent=agent, content=system_message_text, role=Message.Role.SYSTEM)

    def next_message(self):
        self.refresh_from_db()
        last_message = self.message_set.last()
        print(f'Last message role: {last_message.role}')
        print(f'Completed at value for this agent: {self.completed_at}')
        if last_message.role == Message.Role.ASSISTANT or self.completed_at:
            print('return (assistant or completed)')
            return None
        if self.busy_thinking:
            print('busy thinking')
            return last_message
        else: 
            print('busy thinking')
            self.busy_thinking = True
            self.save()
        
        # Otherwise last message was from the user, was the return from a function, or was the starting system message
        # So we need to send it to GPT
        try:
            response = create_chat_completion(self.message_set.all(), self.callable_functions, call_first_function=False)  # (current_call == max_calls)
        except Exception as e:
            error_message = f'Unfortunately there was a problem querying the OpenAI API. Try again later, and please report this error to the developers. Full error: {e}'
            self.busy_thinking = False
            self.save()
            print('busy thinking set to false - return error with openai')
            return Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=error_message)
        
        response_message = response.choices[0].message
    
        if not response_message.tool_calls:  # It's a simple assistant message
            self.busy_thinking = False
            self.save()
            print('busy thinking set to false - returning assistant message')
            return Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=response_message.content)

        fn = response_message.tool_calls[0].function
        try:
            function_call = get_function(fn)
            function_result = self.run_function(function_call)
        except (json.decoder.JSONDecodeError, Exception) as e:
            error = f'ERROR WITH FUNCTION CALLING RESULT: Invalid JSON or code provided in your last response ({response_message.tool_calls[0].function.arguments}), please try again. \nError: {e}'
            return self.create_function_message(response_message, error)
        
        return self.create_function_message(response_message, function_result)
    
    def run_function(self, function_call):
        function_model_class = getattr(agent_tools, function_call.name[0].upper() + function_call.name[1:])
        function_model_obj = function_model_class(**function_call.arguments)
        return function_model_obj.run()

    def create_function_message(self, response_message, function_message_content):
        print(f'Function message result: {function_message_content}')
        if response_message.content:
            function_message_content = f"'''\nThoughts: {response_message.content}\n'''\n" + function_message_content
        function_message = Message(agent=self,role=Message.Role.FUNCTION, function_name=response_message.tool_calls[0].function.name, content=function_message_content)
        if response_message.tool_calls[0].id:
            function_message.function_id = response_message.tool_calls[0].id
        function_message.save()
        self.refresh_from_db()  # Necessary so that completed_at doesn't get overwritten
        self.busy_thinking = False
        self.save()
        print('busy thinking set to false - returning function message or possibly error')
        return function_message
        

class Message(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField(default='')

    class Role(models.TextChoices):
        USER = 'user'
        SYSTEM = 'system'
        ASSISTANT = 'assistant'
        FUNCTION = 'function'
    role = models.CharField(max_length=10, choices=Role.choices)

    # Only for 'function' role messages
    function_name = models.CharField(max_length=200, blank=True)
    function_id = models.CharField(max_length=200, blank=True)

    @property
    def openai_schema(self):
        schema = { 'content': self.content, 'role': self.role }
        if self.role == Message.Role.FUNCTION:
            schema.update({ 'name': self.function_name })
            if self.function_id:
                schema.update({ 'tool_call_id': self.function_id })
        return schema

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']

