from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api import agent_tools
from api.helpers.openai_helpers import check_function_args, create_chat_completion
from picklefield.fields import PickledObjectField
import pandas as pd
from django.template.loader import render_to_string
from os import path


class Dataset(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
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
        get_latest_by = 'created_at'
        ordering = ['created_at']


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=300, unique=True)
    text = models.CharField(max_length=5000)
    per_table = models.BooleanField()
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


class Agent(models.Model):  
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    @property
    def callable_functions(self):
        return [getattr(agent_tools, f) for f in self.task.functions]

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']

    def get_next_assistant_message_for_user(self):
        if self.completed_at is not None:
            return None
        
        last_message = self.message_set.last()
        if not last_message:
            print('-------No last message for this:-------')
            print(self.task.name)
            self.task.create_agents_with_system_messages(dataset=self.dataset)
            last_message = self.message_set.last() 
            return last_message
        if last_message.role == Message.Role.ASSISTANT:
            return last_message
        
        return self.run()

    @classmethod
    def create_with_system_message(cls, tables, **kwargs):
        agent = cls.objects.create(**kwargs)
        system_message_text = render_to_string('prompt.txt', context={ 'agent': agent, 'task_text': agent.task.text, 'agent_tables': tables, 'all_tasks_count': Task.objects.all().count() })
        print(system_message_text)
        Message.objects.create(agent=agent, content=system_message_text, role=Message.Role.SYSTEM)
        return agent

    def run(self, current_call=0, max_calls=10):
        response = create_chat_completion(self.message_set.all(), self.callable_functions, call_first_function=(current_call == max_calls))
        
        # Note - Assistant messages which have function calls usually do not have content, but if they do it's fine to show it to the user
        message_content = response.choices[0].message.content
        if message_content:
            message = Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=message_content)

        function_call = check_function_args(response)
        if function_call:
            function_message = Message.objects.create(agent=self, role=Message.Role.FUNCTION, function_name=function_call.name)
            if function_call.id:
                function_message.function_id = function_call.id
                function_message.save()
            function_result = self.run_function(function_call)
            print(f'Function result: {function_result}')
            function_message.content = function_result
            function_message.save()
        
            # If this was not the SetAgentTaskToComplete function we need to feed it back to GPT4
            if function_call.name != agent_tools.SetAgentTaskToComplete.__name__:
                return self.run(current_call=current_call+1, max_calls=max_calls)
            else:
                message = function_message

        return message
    
    def run_function(self, function_call):
        function_model_class = getattr(agent_tools, function_call.name[0].upper() + function_call.name[1:])
        function_model_obj = function_model_class(**function_call.arguments)  # I think pydantic validation is called here automatically when we instantiate, so we should probably have a try/catch here and feed the error back to GPT4 in case it got the args really wrong 
        return function_model_obj.run()


class Table(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)

    @property
    def df_json(self):
        return self.df.to_json(orient='records', date_format='iso')

    def _snapshot_df(self):
        max_rows, max_columns, max_str_len = 5, 5, 70

        # Truncate long strings in cells
        df = self.df.apply(lambda col: col.astype(str).map(lambda x: (x[:max_str_len - 3] + '...') if len(x) > max_str_len else x))

        # Truncate rows
        if len(df) > max_rows:
            top = df.head(max_rows // 2)
            bottom = df.tail(max_rows // 2)
            middle = pd.DataFrame({col: ['...'] for col in df.columns}, index=[0])  # Use a temporary numeric index for middle
            df = pd.concat([top, middle, bottom], ignore_index=True)

        # Truncate columns
        if len(df.columns) > max_columns:
            left = df.iloc[:, :max_columns//2]
            right = df.iloc[:, -max_columns//2:]
            middle = pd.DataFrame({ '...': ['...']*len(df) }, index=df.index)
            df = pd.concat([left, middle, right], axis=1)
        
        return df.fillna('')

    @property
    def str_snapshot(self):
        self.make_columns_unique(self.df)
        original_rows, original_cols = self.df.shape
        return self._snapshot_df().to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

    def save(self, *args, **kwargs):
        self.df = self.make_columns_unique(self.df)
        super().save(*args, **kwargs)
    
    def make_columns_unique(self, df):
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():  # Iterate over unique duplicates.
            dup_indices = cols[cols == dup].index  # Get indices of all occurrences of the duplicate.
            for i, idx in enumerate(dup_indices):
                cols[idx] = f"{dup}_{i+1}" if i != 0 else dup  # Rename duplicates uniquely, preserve first occurrence name.
        df.columns = cols
        return df

class Message(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=10000, blank=True)

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


class Metadata(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=2000, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
