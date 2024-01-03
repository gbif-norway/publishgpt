from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api import agent_tools
from api.helpers.openai_helpers import openai_function_details, create_chat_completion
from picklefield.fields import PickledObjectField
import pandas as pd
from datetime import datetime
from django.template.loader import render_to_string
from os import path
from django.dispatch import receiver
from django.db.models.signals import pre_save


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
    
    @property
    def active_tables(self):
        return Table.objects.filter(dataset=self, deleted_at=None, stale_at=None, temporary_duplicate_of=None)
    
    def backup_tables_and_get_ids(self):
        backup_ids = []
        for t in self.active_tables:
            t.temporary_duplicate_of_id = t.id
            t.id = None
            t.save()
            backup_ids.append(t.id)
        return backup_ids

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']


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
        active_tables = dataset.active_tables
        agents = []
        if self.per_table:  # One agent per table
            for table in active_tables:
                agent = Agent.create_with_system_message(dataset=dataset, task=self, tables=[table])
                agents.append(agent)
        else:  # One agent for all the tables
            agent = Agent.create_with_system_message(dataset=dataset, task=self, tables=active_tables)
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
        # import pdb; pdb.set_trace()
        if last_message.role == Message.Role.ASSISTANT:
            return last_message
        
        return self.run()

    @classmethod
    def create_with_system_message(cls, tables, **kwargs):
        agent = cls.objects.create(**kwargs)
        system_message_text = render_to_string('prompt.txt', context={ 'agent': agent, 'task_text': agent.task.text, 'agent_tables': tables, 'all_tasks_count': Task.objects.all().count() })
        if agent.task.name == 'mapping':
            system_message_text += render_to_string('dwc.txt')
        print(system_message_text)

        system_message = Message.objects.create(agent=agent, content=system_message_text, role=Message.Role.SYSTEM)
        for table in tables:
            MessageTableAssociation.objects.create(message=system_message, table=table)
        return agent

    def run(self, current_call=0, max_calls=10):
        response = create_chat_completion(self.message_set.all(), self.callable_functions, call_first_function=(current_call == max_calls))
        
        # Note - Assistant messages which have function calls usually do not have content, but if they do it's fine to show it to the user
        message_content = response['choices'][0]['message'].get('content')
        if message_content:
            message = Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=message_content)
            print('message created')

        function_name, function_args = openai_function_details(response)
        if function_name:
            function_message = Message.objects.create(agent=self, role=Message.Role.FUNCTION, function_name=function_name)
            function_result = self.run_function(function_name, function_args, function_message)
            print(f'Function result: {function_result}')
            function_message.content = function_result
            function_message.save()
        
            # If this was not the SetAgentTaskToComplete function we need to feed it back to GPT4
            if function_name != agent_tools.SetAgentTaskToComplete.__name__:
                return self.run(current_call=current_call+1, max_calls=max_calls)
            else:
                message = function_message

        return message
    
    def run_function(self, function_name, function_args, function_message):
        function_model_class = getattr(agent_tools, function_name)
        function_model_obj = function_model_class(**function_args)  # I think pydantic validation is called here automatically when we instantiate, so we should probably have a try/catch here and feed the error back to GPT4 in case it got the args really wrong 

        if function_name == agent_tools.Python.__name__:
            return function_model_obj.run(function_message)
        return function_model_obj.run()


class Table(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    stale_at = models.DateTimeField(null=True, blank=True)
    temporary_duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True) 
    # Could have 'update_of' foreign key to self, in order to at least try and track a little bit of changes?
    # Or... an alternative and slightly scary thought... maybe remove the fk constraint and just store the pk as an int?

    @property
    def df_json(self):
        try:
            return self.df.to_json(orient='records', date_format='iso')
        except ValueError:
            self.df = self.df

    def soft_delete(self):
        self.deleted_at = datetime.now()
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

    @property
    def str_snapshot(self):
        original_rows, original_cols = self.df.shape
        return self._snapshot_df().to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

@receiver(pre_save, sender=Table)
def rename_duplicate_columns(sender, instance, **kwargs):
    df = instance.df

    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols

    instance.df = df


class Message(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=10000, blank=True)
    faked = models.BooleanField(default=False)

    class Role(models.TextChoices):
        USER = 'user'
        SYSTEM = 'system'
        ASSISTANT = 'assistant'
        FUNCTION = 'function'
    role = models.CharField(max_length=10, choices=Role.choices)

    # Only for 'function' role messages
    function_name = models.CharField(max_length=200, blank=True)

    # For system and function messages
    tables = models.ManyToManyField(Table, through='MessageTableAssociation', blank=True)

    @property
    def openai_schema(self):
        if self.role == Message.Role.FUNCTION:
            return { 'content': self.content, 'role': self.role, 'name': self.function_name }
        return { 'content': self.content, 'role': self.role }

    class Meta:
        get_latest_by = 'created_at'
        ordering = ['created_at']


class MessageTableAssociation(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)

    class Operation(models.TextChoices):
        CREATE = 'c'
        UPDATE = 'u'
        DELETE = 'd'
    operation = models.CharField(max_length=1, choices=Operation.choices, null=True, blank=True)


class Metadata(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=500, blank=True)
    description = models.CharField(max_length=2000, blank=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
