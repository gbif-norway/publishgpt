"""Check actual request endpoints, not just unchanged conversation text.

The fake implements only the documented explicit endpoint lookup rule. It does
not model tokenisation, provider routing or eviction and predicts no billable
savings. No model calls or dataset writes are made.
"""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from api.helpers.openai_helpers import create_response_message, _messages_to_responses_input
from api.models import Agent


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(part) for key, part in value.items() if key != 'prompt_cache_breakpoint'}
    if isinstance(value, list):
        if value and all(isinstance(part, dict) and part.get('type') == 'input_text' for part in value):
            return ''.join(part['text'] for part in value)
        return [canonical(part) for part in value]
    return value


def boundaries(items):
    endpoints = []
    for index, item in enumerate(items):
        parts = item.get('output', item.get('content', []))
        if isinstance(parts, list) and any(isinstance(part, dict) and 'prompt_cache_breakpoint' in part for part in parts):
            endpoints.append((index, json.dumps(strip_markers(items[:index + 1]), sort_keys=True)))
    return endpoints


def strip_markers(value):
    """Preserve wire representation; only cache annotations are non-content."""
    if isinstance(value, dict):
        return {key: strip_markers(part) for key, part in value.items() if key != 'prompt_cache_breakpoint'}
    if isinstance(value, list):
        return [strip_markers(part) for part in value]
    return value


class EndpointCache:
    def __init__(self):
        self.saved = set()

    def use(self, points):
        match = max((index for index, prefix in points if prefix in self.saved), default=-1)
        self.saved.update(prefix for _, prefix in points)
        return match


@override_settings(OPENAI_TOOL_HISTORY_TURNS=8, OPENAI_FULL_TOOL_HISTORY_TURNS=2, OPENAI_COMPACT_TOOL_CHARS=1000)
class HistoryCacheTests(SimpleTestCase):
    def message(self, history, obj):
        history.append(SimpleNamespace(id=max((message.id for message in history), default=0) + 1, openai_obj=obj))

    def append_turn(self, history, turn, size=6000, parallel=1):
        calls = [{'id': f'call-{turn}-{part}', 'type': 'function', 'function': {
            'name': 'Python', 'arguments': json.dumps({'code': f'print({turn}, {part})'}),
        }} for part in range(parallel)]
        self.message(history, {'role': 'assistant', 'content': '', 'tool_calls': calls})
        for part, call in enumerate(calls):
            self.message(history, {'role': 'tool', 'tool_call_id': call['id'], 'content': f'{turn}/{part}:' + 'x' * size})

    def request(self, history):
        with patch.object(Agent, 'message_set', SimpleNamespace(all=lambda: history)):
            messages = Agent().messages_for_model()
        unmarked = _messages_to_responses_input(messages)
        with patch('api.helpers.openai_helpers._query_with_flex_fallback') as query:
            query.return_value = SimpleNamespace(id='fake', status='completed', output=[])
            create_response_message(messages, [], model='gpt-6.1-sol', reasoning_effort='high',
                                    additional_input_items=[{'role': 'system', 'content': f'Dynamic state {len(history)}'}])
        request = query.call_args.args[0]
        self.assertEqual(canonical(request['input'][:-1]), canonical(unmarked))
        self.assertEqual(request['input'][-1], {'role': 'system', 'content': f'Dynamic state {len(history)}'})
        self.assertEqual(request['prompt_cache_options'], {'mode': 'explicit'})
        points = boundaries(request['input'])
        self.assertLessEqual(len(points), 4)
        self.assertEqual(points[0][0], 0)
        self.assertTrue(all(index < len(request['input']) - 1 for index, _ in points))
        return request, points

    def test_compacted_frontier_is_reused_between_batch_drops(self):
        for parallel, size in ((1, 6000), (3, 6000), (1, 40)):
            with self.subTest(parallel=parallel, size=size):
                history = []
                self.message(history, {'role': 'system', 'content': 'Frozen opening'})
                self.message(history, {'role': 'user', 'content': 'Prepare this dataset'})
                cache, old_cache = EndpointCache(), EndpointCache()
                misses = []
                for turn in range(1, 27):
                    self.append_turn(history, turn, size, parallel)
                    request, points = self.request(history)
                    hit = cache.use(points)
                    # Isolate the old endpoint selection using the same new
                    # serialisation. This is not a provider/token simulation.
                    old_hit = old_cache.use([points[0], points[-1]])
                    if turn > 1:
                        self.assertEqual(old_hit, 0, turn)
                    if turn >= 4:
                        if hit == 0:
                            misses.append(turn)
                        if turn not in {17, 25}:
                            self.assertGreater(hit, 0, turn)
                self.assertEqual(misses, [17, 25])

    def test_source_replacement_recovers_without_caching_dynamic_state(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        self.message(history, {'role': 'system', 'content': 'Source version 1', 'source_update': True})
        cache = EndpointCache()
        for turn in range(1, 8):
            if turn == 5:
                self.message(history, {'role': 'system', 'content': 'Source version 2', 'source_update': True})
                self.message(history, {'role': 'user', 'content': 'Use the corrected source'})
            self.append_turn(history, turn)
            request, points = self.request(history)
            hit = cache.use(points)
            if turn == 5:
                self.assertEqual(hit, 0)
            if turn in {6, 7}:
                self.assertGreater(hit, 0)
            self.assertNotIn('cache_checkpoint', json.dumps(request))

    def test_pure_user_history_retains_the_previous_endpoint(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        cache = EndpointCache()
        for turn in range(5):
            self.message(history, {'role': 'user', 'content': f'Question {turn}'})
            request, points = self.request(history)
            hit = cache.use(points)
            if turn:
                self.assertGreater(hit, 0)

    def test_pdf_parts_are_preserved_and_checkpoints_do_not_modify_storage(self):
        # Use the existing attachment hydration contract without uploading files.
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        self.message(history, {'role': 'user', 'content': 'Read the manuscript'})
        parts = [{'type': 'input_text', 'text': 'Read the manuscript'},
                 {'type': 'input_file', 'file_id': 'file-existing', 'filename': 'paper.pdf'}]
        original = copy.deepcopy([message.openai_obj for message in history])
        with patch('api.helpers.openai_helpers._hydrate_user_message_content_with_pdf_attachments', return_value=parts):
            request, _ = self.request(history)
        self.assertEqual(canonical(request['input'][1]['content']), canonical(parts))
        self.assertEqual([message.openai_obj for message in history], original)

    def test_text_ending_attachment_parts_are_not_mutated(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        self.message(history, {'role': 'user', 'content': 'Read the manuscript'})
        parts = [{'type': 'input_file', 'file_id': 'file-existing'},
                 {'type': 'input_text', 'text': 'Read the manuscript'}]
        original = copy.deepcopy(parts)
        with patch('api.helpers.openai_helpers._hydrate_user_message_content_with_pdf_attachments', return_value=parts):
            request, _ = self.request(history)
        self.assertEqual(parts, original)
        self.assertIn('prompt_cache_breakpoint', request['input'][1]['content'][-1])

    def test_pdf_attachment_does_not_move_tool_checkpoint_indices(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        # No user message: the PDF attachment helper appends one after history.
        for turn in range(1, 5):
            self.append_turn(history, turn)
        file_parts = [{'file_id': 'file-existing', 'filename': 'paper.pdf'}]
        for turn in (5, 6):
            self.append_turn(history, turn)
            with patch.object(Agent, 'message_set', SimpleNamespace(all=lambda: history)):
                messages = Agent().messages_for_model()
            with patch('api.helpers.openai_helpers._prepare_pdf_file_inputs', return_value=file_parts), \
                    patch('api.helpers.openai_helpers._query_with_flex_fallback') as query:
                query.return_value = SimpleNamespace(id='fake', status='completed', output=[])
                create_response_message(messages, [], model='gpt-6.1-sol', pdf_user_files=[object()],
                                        additional_input_items=[{'role': 'system', 'content': 'Dynamic state'}])
            items = query.call_args.args[0]['input']
            points = boundaries(items)
            checkpoint_calls = {items[index].get('call_id') for index, _ in points}
            self.assertIn(f'call-{turn-3}-0', checkpoint_calls)
            self.assertIn(f'call-{turn-2}-0', checkpoint_calls)
            self.assertEqual(items[-2]['content'][-1], {'type': 'input_file', 'file_id': 'file-existing'})
            self.assertTrue(all(index < len(items) - 2 for index, _ in points))

    def test_older_model_keeps_original_string_representation(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        self.message(history, {'role': 'user', 'content': 'Prepare this dataset'})
        self.append_turn(history, 1)
        with patch('api.helpers.openai_helpers._query_with_flex_fallback') as query:
            query.return_value = SimpleNamespace(id='fake', status='completed', output=[])
            create_response_message(history, [], model='gpt-5.4')
        request = query.call_args.args[0]
        self.assertNotIn('prompt_cache_options', request)
        self.assertIsInstance(request['input'][1]['content'], str)
        self.assertIsInstance(request['input'][-1]['output'], str)
        self.assertEqual(boundaries(request['input']), [])

    def test_checkpoint_uses_last_available_parallel_output(self):
        history = []
        self.message(history, {'role': 'system', 'content': 'Frozen opening'})
        self.message(history, {'role': 'user', 'content': 'Prepare this dataset'})
        for turn in range(1, 5):
            self.append_turn(history, turn, parallel=3)
            # Keep two replies in reverse order; one reply is missing.
            replies = history[-3:]
            history[-3:] = [replies[2], replies[0]]
        with patch.object(Agent, 'message_set', SimpleNamespace(all=lambda: history)):
            messages = Agent().messages_for_model()
        marked = [message for message in messages if getattr(message, 'cache_checkpoint', False)]
        self.assertEqual([m.openai_obj['tool_call_id'] for m in marked], ['call-1-0', 'call-2-0'])
