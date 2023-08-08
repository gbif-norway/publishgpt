from django.test import TestCase
from api.models import Dataset, Agent, Task, Table, Message, MessageTableAssociation
from api.agent_tools import Python
import pandas as pd
from pandas.testing import assert_frame_equal
from unittest.mock import patch

class TestPythonRun(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(file='path/to/file')
        self.task = Task.objects.create(name='Test', text='Test', per_table=False)
        self.agent = Agent.objects.create(dataset=self.dataset, task=self.task)
        self.function_message = Message.objects.create(agent=self.agent, role=Message.Role.FUNCTION, function_name='test_function')

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

    @patch('api.agent_tools.Python.handle_table_backups')
    def test_handle_table_backups_called(self, mock_handle_table_backups):
        python_code = 'a = 1 + 1'
        python_instance = Python(code=python_code)
        python_instance.run(self.function_message)
        mock_handle_table_backups.assert_called_once()


class TestHandleTableBackups(TestCase):
    def setUp(self):
        self.dataset = Dataset.objects.create(file='path/to/file')
        self.task = Task.objects.create(name='Test', text='Test', per_table=False)
        self.agent = Agent.objects.create(dataset=self.dataset, task=self.task)
        self.message = Message.objects.create(agent=self.agent, role=Message.Role.FUNCTION, function_name='test_function')
        self.table1_args = { 'dataset': self.dataset, 'title': 'Table 1', 'df': pd.DataFrame(['some data']) }
        self.table1 = Table.objects.create(**self.table1_args)

    def test_newly_created_tables(self):
        duplicates = self.dataset.backup_tables_and_get_ids()
        new_table = Table.objects.create(dataset=self.dataset, title='New Table', df=pd.DataFrame(['new data']))
        Python.handle_table_backups(self.message, duplicates)

        # Check that the new table is linked with the CREATE operation
        self.assertTrue(MessageTableAssociation.objects.filter(message=self.message, table=new_table, operation=MessageTableAssociation.Operation.CREATE).exists())

    def test_deleted_tables(self):
        # Back up active tables before deleting a table
        duplicates = self.dataset.backup_tables_and_get_ids()
        self.table1.delete()
        Python.handle_table_backups(self.message, duplicates)

        # Check that there's only 1 table with an identical df to the old table, and with a deleted_at
        tables = Table.objects.all()
        self.assertEqual(len(tables), 1)
        assert_frame_equal(tables[0].df, Table(**self.table1_args).df)
        self.assertTrue(tables[0].deleted_at != None)
        self.assertTrue(MessageTableAssociation.objects.filter(message=self.message, table=tables[0], operation=MessageTableAssociation.Operation.DELETE).exists())

    def test_handle_edits(self):
        duplicates = self.dataset.backup_tables_and_get_ids()
        self.table1.df = pd.DataFrame(['updated data'])
        self.table1.save()
        Python.handle_table_backups(self.message, duplicates)

        # There should be two table objects, one back up and one with the latest modifications
        tables = Table.objects.all()
        self.assertEqual(len(tables), 2)

        # The original table should have the original dataframe, and a stale_at
        self.table1.refresh_from_db()
        assert_frame_equal(self.table1.df, self.table1_args['df'])
        self.assertTrue(self.table1.stale_at != None)

        # There should be a new table with the new dataframe 
        new_table = tables.exclude(id=self.table1.id).first()
        # new_tables = self.function_message.agent.dataset.active_tables
        assert_frame_equal(new_table.df, pd.DataFrame(['updated data']))

        # Check the many-to-many link
        self.assertTrue(MessageTableAssociation.objects.filter(message=self.message, table=new_table, operation=MessageTableAssociation.Operation.UPDATE).exists())

    def test_no_changes(self):
        table2 = Table.objects.create(dataset=self.dataset, title='Table 2', df=pd.DataFrame(['other data']))
        duplicates = self.dataset.backup_tables_and_get_ids()
        Python.handle_table_backups(self.message, duplicates)
        
        # Check the two tables remain the same
        tables = Table.objects.all()
        self.assertEqual(list(tables), [self.table1, table2])

        # Check that no MessageTableAssociations are recorded
        self.assertFalse(MessageTableAssociation.objects.filter(message=self.message).exists())
