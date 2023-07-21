from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api.openai_wrapper import chat_completion, functions, prompts
from api.helpers.openai import callable, openai_function_details, function_name_in_text
from picklefield.fields import PickledObjectField
import pandas as pd
from datetime import datetime
import re
from django.template.loader import render_to_string
from os import path
from django.db.models import Count, Max, F


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

    def get_active_datasetframes(self):
        # Get all of the dataframes which either have no children (i.e. are leaf nodes) or are the most recent children - i.e., all the active ones we are using currently
        # TODO we really need to modify this to take into account deleted dataframes
        dsfs = DatasetFrame.objects.filter(dataset=self)
        leaf_datasetframes = dsfs.annotate(num_children=Count('datasetframe')).filter(num_children=0)
        recent_datasetframe_ids = dsfs.values('parent').annotate(recent_child_id=Max('id')).values_list('recent_child_id', flat=True)
        recent_datasetframes = DatasetFrame.objects.filter(id__in=recent_datasetframe_ids)
        return leaf_datasetframes | recent_datasetframes


class Task(models.Model):  # See tasks.yaml for the only objects this model is populated with
    name = models.CharField(max_length=300, unique=True)
    system_message_template = models.CharField(max_length=5000)
    per_datasetframe = models.BooleanField()

    class Meta:
        get_latest_by = 'id'
        ordering = ['id']

    @property
    def functions(self):
        return [functions.Python.__name__, functions.SetTaskToComplete.__name__]

    def create_agents(self, dataset:Dataset):
        active_datasetframes = dataset.get_active_datasetframes()
        agents = []

        if self.per_datasetframe:  # One agent per datasetframe
            for datasetframe in active_datasetframes:
                agent = Agent.objects.create(_functions=self.functions, dataset=dataset, task=self)
                AgentDatasetFrame.objects.create(agent=agent, dataset_frame=datasetframe)
                system_message = render_to_string('prompt.txt', context={ 'agent': agent, 'agent_datasetframes': datasetframe })
                Message.objects.create(agent=agent, content=system_message, role=Message.Role.SYSTEM)
                agents.append(agent)
        else:  # One agent for all the datasetframes
            agent = Agent.objects.create(_functions=self.functions, dataset=dataset, task=self)
            for datasetframe in active_datasetframes:
                AgentDatasetFrame.objects.create(agent=agent, dataset_frame=datasetframe)
            system_message = render_to_string('prompt.txt', context={'agent': agent, 'agent_datasetframes': active_datasetframes })
            Message.objects.create(agent=agent, content=system_message, role=Message.Role.SYSTEM)
            agents.append(agent)

        return agents


class Agent(models.Model):  
    created = models.DateTimeField(auto_now_add=True)
    completed = models.DateTimeField(null=True, blank=True)
    _functions = ArrayField(base_field=models.CharField(max_length=500))
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    @property
    def callable_functions(self):
        return [callable(f) for f in self._functions]

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

    def run(self, allow_user_feedack=True, current_call=0, max_calls=10):
        stop_loop = current_call == max_calls
        response = chat_completion.create(self.message_set.all(), self.callable_functions, call_first_function=stop_loop)
        
        # Run a function if GPT has asked for a function to be called, and send the results back to GPT without user feedback
        function_name, function_args = openai_function_details(response)
        if function_name:
            Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=response)
            function_result = getattr(functions, function_name).run(**function_args)
            import pdb; pdb.set_trace()
            if function_result:
                Message.objects.create(agent=self, role=Message.Role.FUNCTION, content=function_result, function_name=function_name)
                return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)
            return None

        # Store GPT's message
        message = Message.objects.create(agent=self, role=Message.Role.ASSISTANT, content=response['choices'][0]['message']['content'])

        # If GPT didn't call the function properly or if we don't want user feedback, ask it to call a function
        if not allow_user_feedack or function_name_in_text(self._functions, message.content):
            message = Message.objects.create(agent=self, role=Message.Role.USER, content='Please respond with a function call, not text.')
            return self.run(allow_user_feedack=allow_user_feedack, current_call=current_call+1, max_calls=max_calls)

        # Return GPT's message for user feedback
        return message


class DatasetFrame(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    problems = ArrayField(base_field=models.CharField(max_length=500), null=True, blank=True)
    parent = models.ForeignKey('DatasetFrame', on_delete=models.CASCADE, blank=True, null=True)
    deleted = models.DateTimeField(null=True, blank=True)  # Is null if the dataset is not deleted

    def soft_delete(self):
        self.deleted = datetime.now()
        self.save()

    def __str__(self, max_rows=5, max_columns=5, max_str_len=70):
        max_rows = max(max_rows, 5)  # At least 5 to show truncation correctly
        max_columns = max(max_columns, 5)  # At least 5 to show truncation correctly
        original_rows, original_cols = self.df.shape

        # Truncate long strings in cells
        df = self.df.astype(str).applymap(lambda x: (x[:max_str_len - 3] + '...') if len(x) > max_str_len else x)

        if len(df) > max_rows:
            top = df.head(max_rows // 2)
            bottom = df.tail(max_rows // 2)
            df = pd.concat([top, pd.DataFrame({col: ['...'] for col in df.columns}), bottom])

        if len(df.columns) > max_columns:
            df = df.iloc[:, :max_columns//2].join(pd.DataFrame({ '...': ['...']*len(df) })).join(df.iloc[:, -max_columns//2:])

        return df.to_string() + f"\n\nTitle {self.title}: [{original_rows} rows x {original_cols} columns]"


class AgentDatasetFrame(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    dataset_frame = models.ForeignKey(DatasetFrame, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.agent.dataset != self.dataset_frame.dataset:
            raise ValueError("Agent's Dataset and DatasetFrame's Dataset must be the same")
        super().save(*args, **kwargs)


class Message(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
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
