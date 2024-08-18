from django.test import TestCase
from api.models import Dataset, Agent, Task, Message
from api.agent_tools import Python
import pandas as pd
from pandas.testing import assert_frame_equal
from unittest.mock import patch

class TestPythonRun(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(file='path/to/file')
        self.task = Task.objects.create(name='Test', text='Test', per_table=False)
        self.agent = Agent.objects.create(dataset=self.dataset, task=self.task)
        self.function_message = Message.objects.create(agent=self.agent, role=Message.Role.TOOL, function_name='test_function')

    def test_successful_execution_without_output(self):
        python_code = 'a = 1 + 1'
        python_instance = Python(code=python_code)
        result = python_instance.run(self.function_message)
        self.assertIn('executed successfully without errors', result.lower())

    def test_successful_execution_with_output(self):
        python_code = 'print("Hello, World!")'
        python_instance = Python(code=python_code)
        result = python_instance.run(self.function_message)
        self.assertIn('Hello, World!', result)

    def test_exception_handling(self):
        python_code = '1 / 0'  # Code that raises an exception
        python_instance = Python(code=python_code)
        result = python_instance.run(self.function_message)
        self.assertIn('ZeroDivisionError', result)
