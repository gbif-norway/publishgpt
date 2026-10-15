import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from openai import APITimeoutError

from api.agent_turns import process_next_agent_turn, queue_agent_turn, reconcile_recent_work
from api.models import Agent, AgentTurnJob, CustomUser, Dataset, Message, Task


class AgentTurnQueueTests(TestCase):
    def setUp(self):
        # TestCase keeps one transaction open across each test; the production
        # worker closes idle connections between independent transactions.
        close_connections = patch('api.agent_turns.close_old_connections')
        close_connections.start()
        self.addCleanup(close_connections.stop)
        self.user = CustomUser.objects.create_user(username='turn-user', password='test')
        self.dataset = Dataset.objects.create(user=self.user, title='Queued workflow')
        self.task = Task.objects.create(name='Data transformation', text='Transform', order=1)
        self.agent = Agent.objects.create(dataset=self.dataset, task=self.task)
        self.message = Message.objects.create(agent=self.agent, openai_obj={
            'role': 'user', 'content': 'Continue',
        })

    def test_polling_dataset_does_not_run_turns(self):
        self.client.force_login(self.user)
        with patch.object(Agent, 'next_message') as next_message:
            first = self.client.get(f'/api/datasets/{self.dataset.id}/')
            second = self.client.get(f'/api/datasets/{self.dataset.id}/')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(AgentTurnJob.objects.exists())
        next_message.assert_not_called()

    def test_user_message_queues_without_refresh(self):
        self.client.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                '/api/messages/',
                data=json.dumps({'agent': self.agent.id, 'openai_obj': {
                    'role': 'user', 'content': 'Proceed',
                }}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AgentTurnJob.objects.get().requested_after_message_id,
                         self.agent.message_set.last().id)

    def test_recent_legacy_work_is_recovered_without_a_browser(self):
        self.assertFalse(AgentTurnJob.objects.exists())

        reconcile_recent_work()

        self.assertEqual(AgentTurnJob.objects.get().requested_after_message_id,
                         self.message.id)

    def test_upload_queues_work_even_without_following_browser_message(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.dataset.handle_source_change(queue_delay_seconds=15)

        self.assertTrue(self.agent.message_set.last().openai_obj.get('source_update'))
        job = AgentTurnJob.objects.get()
        self.assertEqual(job.requested_after_message_id, self.agent.message_set.last().id)
        self.assertGreater(job.available_at, timezone.now() + timedelta(seconds=10))
        self.assertFalse(process_next_agent_turn())

        with self.captureOnCommitCallbacks(execute=True):
            self.client.force_login(self.user)
            response = self.client.post(
                '/api/messages/',
                data=json.dumps({'agent': self.agent.id, 'openai_obj': {
                    'role': 'user', 'content': 'The new file contains observations.',
                }}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 201)
        job.refresh_from_db()
        self.assertEqual(job.requested_after_message_id, self.agent.message_set.last().id)
        self.assertLessEqual(job.available_at, timezone.now())

    def test_worker_runs_claimed_turn_and_clears_job(self):
        queue_agent_turn(self.agent)

        def answer(agent):
            Message.objects.create(agent=agent, openai_obj={
                'role': 'assistant', 'content': 'Please review.',
            })

        with patch.object(Agent, 'next_message', answer):
            self.assertTrue(process_next_agent_turn())

        self.assertFalse(AgentTurnJob.objects.exists())

    def test_stale_claim_recovers_busy_flag(self):
        job = queue_agent_turn(self.agent)
        job.claimed_at = timezone.now() - timedelta(hours=2)
        job.save(update_fields=['claimed_at'])
        Agent.objects.filter(pk=self.agent.pk).update(busy_thinking=True)

        def answer(agent):
            Message.objects.create(agent=agent, openai_obj={
                'role': 'assistant', 'content': 'Please review.',
            })

        with patch.object(Agent, 'next_message', answer):
            self.assertTrue(process_next_agent_turn())

        self.assertFalse(Agent.objects.get(pk=self.agent.pk).busy_thinking)

    def test_superseded_turn_is_not_replayed(self):
        queue_agent_turn(self.agent)
        Message.objects.create(agent=self.agent, openai_obj={'role': 'user', 'content': 'Changed'})

        with patch.object(Agent, 'next_message') as next_message:
            self.assertTrue(process_next_agent_turn())

        next_message.assert_not_called()
        self.assertEqual(AgentTurnJob.objects.get().requested_after_message_id,
                         self.agent.message_set.last().id)

    def test_interrupted_tool_call_reports_failure_instead_of_disappearing(self):
        job = queue_agent_turn(self.agent)
        job.claimed_at = timezone.now() - timedelta(hours=2)
        job.save(update_fields=['claimed_at'])
        Message.objects.create(agent=self.agent, openai_obj={
            'role': Message.Role.ASSISTANT,
            'content': '',
            'tool_calls': [{
                'id': 'tool-1',
                'type': 'function',
                'function': {'name': 'Python', 'arguments': '{}'},
            }],
        })

        with patch.object(Agent, 'next_message') as next_message:
            self.assertTrue(process_next_agent_turn())

        next_message.assert_not_called()
        self.assertFalse(AgentTurnJob.objects.exists())
        self.assertTrue(self.agent.message_set.last().openai_obj.get('workflow_error'))

    def test_tool_result_continues_without_browser_polling(self):
        queue_agent_turn(self.agent)

        def turn(agent):
            role = 'tool' if agent.message_set.last().role == Message.Role.USER else 'assistant'
            Message.objects.create(agent=agent, openai_obj={
                'role': role, 'content': 'Result' if role == 'tool' else 'Please review.',
            })

        with patch.object(Agent, 'next_message', turn):
            self.assertTrue(process_next_agent_turn())
            self.assertEqual(AgentTurnJob.objects.get().requested_after_message_id,
                             self.agent.message_set.last().id)
            self.assertTrue(process_next_agent_turn())

        self.assertFalse(AgentTurnJob.objects.exists())

    def test_gbif_recheck_is_scheduled_without_busy_polling(self):
        future = timezone.now() + timedelta(minutes=10)
        Message.objects.create(agent=self.agent, openai_obj={
            'role': 'tool',
            'content': json.dumps({
                'status': 'RUNNING', 'validation_key': 'test',
                'next_recheck_at': future.isoformat(),
            }),
        })
        job = queue_agent_turn(self.agent)

        self.assertGreaterEqual(job.available_at, future)
        self.assertFalse(process_next_agent_turn())

    def test_completed_stage_starts_next_stage_without_browser_polling(self):
        next_task = Task.objects.create(name='Next stage', text='Continue', order=2)
        queue_agent_turn(self.agent)

        def create_agent(task, dataset):
            next_agent = Agent.objects.create(dataset=dataset, task=task)
            Message.objects.create(agent=next_agent, openai_obj={
                'role': Message.Role.SYSTEM, 'content': 'Start the next stage.',
            })
            return next_agent

        def complete(agent):
            agent.completed_at = timezone.now()
            agent.save(update_fields=['completed_at'])
            Message.objects.create(agent=agent, openai_obj={
                'role': Message.Role.TOOL, 'content': 'Complete',
            })

        with patch.object(Agent, 'next_message', complete), patch.object(
            Task, 'create_agent_with_system_messages', create_agent,
        ):
            self.assertTrue(process_next_agent_turn())

        next_agent = Agent.objects.get(dataset=self.dataset, task=next_task)
        self.assertEqual(AgentTurnJob.objects.get().agent_id, next_agent.id)

        def ask(agent):
            Message.objects.create(agent=agent, openai_obj={
                'role': Message.Role.ASSISTANT, 'content': 'Your decision?',
            })

        with patch.object(Agent, 'next_message', ask):
            self.assertTrue(process_next_agent_turn())

        self.assertFalse(AgentTurnJob.objects.exists())
        self.assertEqual(next_agent.message_set.last().role, Message.Role.ASSISTANT)

    def test_transient_model_error_is_retried_then_reported(self):
        queue_agent_turn(self.agent)
        timeout = APITimeoutError(request=None)

        with patch('api.models.create_response_message', side_effect=timeout):
            with self.assertRaises(APITimeoutError):
                process_next_agent_turn()
            job = AgentTurnJob.objects.get()
            self.assertEqual(job.failure_count, 1)
            self.assertIsNone(job.claimed_at)
            self.assertGreater(job.available_at, timezone.now())
            self.assertEqual(self.agent.message_set.last().id, self.message.id)
            self.assertFalse(Agent.objects.get(pk=self.agent.pk).busy_thinking)

            for _ in range(2):
                AgentTurnJob.objects.update(available_at=timezone.now())
                with self.assertRaises(APITimeoutError):
                    process_next_agent_turn()

        self.assertFalse(AgentTurnJob.objects.exists())
        self.assertTrue(self.agent.message_set.last().openai_obj.get('workflow_error'))

    def test_turn_without_progress_backs_off(self):
        queue_agent_turn(self.agent)
        Agent.objects.filter(pk=self.agent.pk).update(busy_thinking=True)

        self.assertTrue(process_next_agent_turn())

        job = AgentTurnJob.objects.get()
        self.assertIsNone(job.claimed_at)
        self.assertGreater(job.available_at, timezone.now() + timedelta(seconds=20))
        self.assertFalse(process_next_agent_turn())

    def test_only_active_agent_job_runs_when_earlier_gate_and_maintenance_are_open(self):
        gate_task = Task.objects.create(name=Task.PREPUBLICATION_QUALITY_TASK, text='Review', order=0)
        maintenance_task = Task.objects.create(name=Task.MAINTENANCE_TASK, text='Maintain', order=2)
        gate = Agent.objects.create(dataset=self.dataset, task=gate_task)
        maintenance = Agent.objects.create(dataset=self.dataset, task=maintenance_task)
        Message.objects.create(agent=gate, openai_obj={'role': 'system', 'content': 'Gate'})
        Message.objects.create(agent=maintenance, openai_obj={'role': 'user', 'content': 'Continue'})
        queue_agent_turn(maintenance)
        queue_agent_turn(gate)
        ran = []

        def answer(agent):
            ran.append(agent.id)
            Message.objects.create(agent=agent, openai_obj={
                'role': 'assistant', 'content': 'Review requested.',
            })

        with patch.object(Agent, 'next_message', answer):
            self.assertTrue(process_next_agent_turn())

        self.assertEqual(ran, [gate.id])
        self.assertFalse(AgentTurnJob.objects.filter(agent=maintenance).exists())
        self.assertFalse(AgentTurnJob.objects.exists())

    def test_duplicate_open_agents_for_same_task_only_run_active_agent(self):
        quality_task = Task.objects.create(
            name=Task.PREPUBLICATION_QUALITY_TASK, text='Review', order=0,
        )
        agents = [Agent.objects.create(dataset=self.dataset, task=quality_task) for _ in range(3)]
        for agent in agents:
            Message.objects.create(agent=agent, openai_obj={'role': 'system', 'content': 'Review'})
            queue_agent_turn(agent)
        active = self.dataset.active_agent()
        ran = []

        def answer(agent):
            ran.append(agent.id)
            Message.objects.create(agent=agent, openai_obj={
                'role': 'assistant', 'content': 'Review requested.',
            })

        with patch.object(Agent, 'next_message', answer):
            self.assertTrue(process_next_agent_turn())

        self.assertEqual(ran, [active.id])
        # Jobs for the inactive duplicates are dropped when a worker reaches them.
        with patch.object(Agent, 'next_message', answer):
            self.assertFalse(process_next_agent_turn())
        self.assertEqual(ran, [active.id])
        self.assertFalse(AgentTurnJob.objects.exists())

    def test_gate_job_waits_while_another_job_for_dataset_has_a_live_claim(self):
        gate_task = Task.objects.create(name=Task.PREPUBLICATION_QUALITY_TASK, text='Review', order=0)
        gate = Agent.objects.create(dataset=self.dataset, task=gate_task)
        Message.objects.create(agent=gate, openai_obj={'role': 'system', 'content': 'Gate'})
        gate_job = queue_agent_turn(gate)
        maintenance_job = AgentTurnJob.objects.create(
            agent=self.agent,
            requested_after_message_id=self.message.id,
            claimed_at=timezone.now(),
        )

        with patch.object(Agent, 'next_message') as next_message:
            self.assertFalse(process_next_agent_turn())

        next_message.assert_not_called()
        gate_job.refresh_from_db()
        maintenance_job.refresh_from_db()
        self.assertIsNone(gate_job.claimed_at)
        self.assertIsNotNone(maintenance_job.claimed_at)

    def test_maintenance_turn_hands_continuation_to_new_quality_gate(self):
        from api.agent_tools import PublishToGBIF

        gate_task = Task.objects.create(name=Task.PREPUBLICATION_QUALITY_TASK, text='Review', order=0)
        maintenance_task = Task.objects.create(name=Task.MAINTENANCE_TASK, text='Maintain', order=2)
        self.agent.completed_at = timezone.now()
        self.agent.save(update_fields=['completed_at'])
        maintenance = Agent.objects.create(dataset=self.dataset, task=maintenance_task)
        Message.objects.create(agent=maintenance, openai_obj={'role': 'user', 'content': 'Continue'})
        queue_agent_turn(maintenance)
        gate_agents = []

        def maintenance_turn(agent):
            if agent.id == maintenance.id:
                self.dataset.dwca_url = 'https://example.org/archive.zip'
                self.dataset.dwca_validation = {
                    'url': self.dataset.dwca_url, 'status': 'FINISHED',
                    'metrics': {'indexeable': True},
                }
                self.dataset.save(update_fields=['dwca_url', 'dwca_validation'])
                PublishToGBIF(agent_id=agent.id).run()
                gate = Agent.objects.get(dataset=self.dataset, task=gate_task)
                gate_agents.append(gate)
                Message.objects.create(agent=agent, openai_obj={
                    'role': 'tool', 'content': 'Quality gate runs next.',
                })
                return
            Message.objects.create(agent=agent, openai_obj={
                'role': 'assistant', 'content': 'Review requested.',
            })

        with self.captureOnCommitCallbacks(execute=True), patch.object(
            Agent, 'next_message', maintenance_turn,
        ):
            self.assertTrue(process_next_agent_turn())

        gate = gate_agents[0]
        self.assertEqual(AgentTurnJob.objects.get().agent_id, gate.id)
        with patch.object(Agent, 'next_message', maintenance_turn):
            self.assertTrue(process_next_agent_turn())
        self.assertFalse(AgentTurnJob.objects.exists())
        self.assertEqual(gate.message_set.last().role, Message.Role.ASSISTANT)

    def test_stale_job_of_completed_stage_still_starts_the_next_stage(self):
        # A worker crashed after the stage completed but before its job finished.
        next_task = Task.objects.create(name='Next stage', text='Continue', order=2)
        queue_agent_turn(self.agent)
        self.agent.completed_at = timezone.now()
        self.agent.save(update_fields=['completed_at'])
        AgentTurnJob.objects.update(claimed_at=timezone.now() - timedelta(days=1))

        def create_agent(task, dataset):
            next_agent = Agent.objects.create(dataset=dataset, task=task)
            Message.objects.create(agent=next_agent, openai_obj={
                'role': Message.Role.SYSTEM, 'content': 'Start the next stage.',
            })
            return next_agent

        with patch.object(Task, 'create_agent_with_system_messages', create_agent):
            self.assertTrue(process_next_agent_turn())

        next_agent = Agent.objects.get(dataset=self.dataset, task=next_task)
        self.assertEqual(AgentTurnJob.objects.get().agent_id, next_agent.id)

    def test_conversion_dataset_job_is_dropped_without_a_turn(self):
        self.dataset.workflow_type = Dataset.WorkflowType.DWCA_CONVERSION
        self.dataset.save(update_fields=['workflow_type'])
        AgentTurnJob.objects.create(agent=self.agent, requested_after_message_id=self.message.id)

        with patch.object(Agent, 'next_message') as next_message:
            self.assertFalse(process_next_agent_turn())

        next_message.assert_not_called()
        self.assertFalse(AgentTurnJob.objects.exists())

    def test_reply_to_an_inactive_open_agent_is_refused(self):
        gate_task = Task.objects.create(name=Task.PREPUBLICATION_QUALITY_TASK, text='Review', order=0)
        Agent.objects.create(dataset=self.dataset, task=gate_task)
        self.client.force_login(self.user)

        response = self.client.post(
            '/api/messages/',
            data=json.dumps({'agent': self.agent.id, 'openai_obj': {'role': 'user', 'content': 'Hi'}}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('no longer active', response.content.decode())
        self.assertEqual(self.agent.message_set.count(), 1)
