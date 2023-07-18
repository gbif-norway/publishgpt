from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from api.openai_wrapper import chat_completion, functions, prompts
from api.helpers.openai import callable, openai_function_details, function_name_in_text
from picklefield.fields import PickledObjectField


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

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']


class Agent(models.Model):  
    created = models.DateTimeField(auto_now_add=True)
    task_complete = models.BooleanField(null=True, blank=True)
    _functions = ArrayField(base_field=models.CharField(max_length=500))
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    @property
    def callable_functions(self):
        return [callable(f) for f in self._functions]
    
    @classmethod
    def create_with_system_message(cls, system_message, **kwargs):
        agent = cls.objects.create(**kwargs)

        # Add the first system message to the agent automatically
        content = prompts.agent_system_message.format(dataset_id=agent.dataset.id, agent_id=agent.id, body=system_message)
        Message.objects.create(agent=agent, content=content, role=Message.Role.SYSTEM)

        # Add default Task Complete function as well 
        agent._functions = [functions.SetTaskToComplete.classname] + agent._functions
        return agent

    class Meta:
        get_latest_by = 'created'
        ordering = ['created']

    def run(self, allow_user_feedack=True, current_call=0, max_calls=10):
        stop_loop = current_call == max_calls
        response = chat_completion.create(self.message_set.all(), self.callable_functions, call_first_function=stop_loop)
        
        # Run a function if GPT has asked for a function to be called, and send the results back to GPT without user feedback
        function_name, function_args = openai_function_details(response)
        if function_name:
            function_result = getattr(functions, function_name).run(**function_args)
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


class DataFrame(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    df = PickledObjectField()
    description = models.CharField(max_length=2000, blank=True)
    problems = ArrayField(base_field=models.CharField(max_length=500), null=True, blank=True)
    parent = models.ForeignKey('DataFrame', on_delete=models.CASCADE, blank=True, null=True)


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
