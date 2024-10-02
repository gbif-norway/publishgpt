from django.test import TestCase
from api.models import Dataset, Agent, Task, Message
from api.agent_tools import Python, RollBack
import pandas as pd
from pandas.testing import assert_frame_equal
from django.test import TestCase
from api.models import Agent, Dataset, Table, Message
from api.agent_tools import RollBack
from unittest.mock import patch

from django.test import TestCase
from api.models import Agent, Dataset, Table, Message
from api.agent_tools import RollBack
from unittest.mock import patch

class RollBackTestCase(TestCase):

    def setUp(self):
        # Set up your test data here
        self.dataset = Dataset.objects.create(orcid="0000-0002-1825-0097", file="path/to/testfile.xlsx")
        self.agent = Agent.objects.create(dataset=self.dataset, task_id=1)
        self.table = Table.objects.create(dataset=self.dataset, title="Sheet1", df={"col1": [1, 2, 3]})

    @patch('api.agent_tools.discord_bot.send_discord_message')
    def test_run_roll_back(self, mock_send_discord_message):
        # Mock necessary methods and objects
        with patch('api.models.Dataset.get_dfs_from_user_file') as mock_get_dfs, \
             patch('api.models.Table.objects.create') as mock_table_create:
            # Setup return values for mocks
            mock_get_dfs.return_value = {"Sheet1": {"col1": [1, 2, 3]}}
            mock_table_create.return_value = self.table

            rollback = RollBack(agent_id=self.agent.id)
            result = rollback.run()

            # Check that tables were deleted and recreated
            self.assertEqual(Table.objects.filter(dataset=self.dataset).count(), 1)
            self.assertEqual(result['new_table_ids'], [self.table.id])

            # Check that discord message was sent
            mock_send_discord_message.assert_called_once_with(f"Dataset tables rolled back for Dataset id {self.dataset.id}.")

    def test_code_snippets_collection(self):
        # Set up test data for function calls
        msg_content = {
            'tool_calls': [
                {
                    'function': {'name': 'Python', 'arguments': '{"code": "print(1)"}'},
                    'id': 'tool_call_1'
                }
            ]
        }
        result_content = {'content': '1'}

        agent_2 = Agent.objects.create(dataset=self.dataset, task_id=2)
        message_1 = Message.objects.create(agent=self.agent, openai_obj=msg_content)
        message_2 = Message.objects.create(agent=agent_2, openai_obj=result_content, tool_call_id="tool_call_1")

        rollback = RollBack(agent_id=self.agent.id)
        result = rollback.run()

        expected_snippets = [{
            'code_run': '{"code": "print(1)"}',
            'results': '1'
        }]

        # Check that the code snippets are correctly collected
        self.assertEqual(result['code_snippets'], expected_snippets)

    def test_run_no_code_snippets(self):
        # Run rollback with no code snippets in messages
        rollback = RollBack(agent_id=self.agent.id)
        result = rollback.run()

        # Check that no code snippets are returned
        self.assertEqual(result['code_snippets'], [])

    @patch('api.models.Dataset.get_dfs_from_user_file', side_effect=Exception("Mock Error"))
    def test_run_with_file_error(self, mock_get_dfs):
        rollback = RollBack(agent_id=self.agent.id)
        with self.assertRaises(Exception) as context:
            rollback.run()

        # Ensure that the error raised is due to the file processing issue
        self.assertTrue("Mock Error" in str(context.exception))
        self.assertEqual(Table.objects.filter(dataset=self.dataset).count(), 0)

    def test_run_multiple_tool_calls(self):
        # Set up test data with multiple tool calls in a single message
        msg_content = {
            'tool_calls': [
                {'function': {'name': 'Python', 'arguments': '{"code": "print(1)"}'}, 'id': 'tool_call_1'},
                {'function': {'name': 'Python', 'arguments': '{"code": "print(2)"}'}, 'id': 'tool_call_2'}
            ]
        }
        result_content_1 = {'content': '1'}
        result_content_2 = {'content': '2'}

        Message.objects.create(agent=self.agent, openai_obj=msg_content)
        Message.objects.create(agent=self.agent, openai_obj=result_content_1, tool_call_id="tool_call_1")
        Message.objects.create(agent=self.agent, openai_obj=result_content_2, tool_call_id="tool_call_2")

        rollback = RollBack(agent_id=self.agent.id)
        result = rollback.run()

        expected_snippets = [
            {'code_run': '{"code": "print(1)"}', 'results': '1'},
            {'code_run': '{"code": "print(2)"}', 'results': '2'}
        ]

        # Check that multiple tool calls in a single message are correctly processed
        self.assertEqual(result['code_snippets'], expected_snippets)

    @patch('api.models.Table.objects.create')
    def test_partial_failure_roll_back(self, mock_table_create):
        # Simulate a failure during table creation
        mock_table_create.side_effect = Exception("Mock Error during table creation")

        rollback = RollBack(agent_id=self.agent.id)
        with self.assertRaises(Exception):
            rollback.run()

        # Ensure no tables were created
        self.assertEqual(Table.objects.filter(dataset=self.dataset).count(), 0)




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
