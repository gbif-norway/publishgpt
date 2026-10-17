"""Model migrations must preserve Flex routing and complete cost accounting."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from api.conversion_review import service_tier
from api.helpers.openai_helpers import create_response_message
from api.openai_models import model_service_tier
from api.openai_usage import response_usage_defaults


@override_settings(OPENAI_SOL_SERVICE_TIER="flex", OPENAI_LUNA_SERVICE_TIER="flex")
class ModelFlexTests(SimpleTestCase):
    @patch("api.helpers.openai_helpers.query_responses_api")
    def test_new_and_snapshot_models_use_flex_and_explicit_cache(self, query):
        query.return_value = SimpleNamespace(id="test", status="completed", output=[])
        for model in ("gpt-6.1-sol", "gpt-6.1-sol-2026-10-01", "gpt-6-luna", "gpt-6-luna-2026-09-01"):
            with self.subTest(model=model):
                message = SimpleNamespace(openai_obj={"role": "system", "content": "Stable instructions"})
                create_response_message([message], [], model=model, reasoning_effort="high")
                args = query.call_args.args[0]
                self.assertEqual(args["service_tier"], "flex")
                self.assertEqual(args["reasoning"], {"effort": "high"})
                self.assertEqual(args["prompt_cache_options"], {"mode": "explicit"})
                self.assertEqual(service_tier(model, "flex"), "flex")
        self.assertEqual(model_service_tier("gpt-6-sol"), "flex")
        self.assertEqual(model_service_tier("gpt-6-astra"), "default")

    @override_settings(OPENAI_LUNA_SERVICE_TIER="default")
    def test_luna_standard_override_does_not_disable_sol_flex(self):
        self.assertEqual(model_service_tier("gpt-6-luna"), "default")
        self.assertEqual(service_tier("gpt-6-luna", "flex"), "default")
        self.assertEqual(model_service_tier("gpt-6.1-sol"), "flex")
        self.assertEqual(service_tier("gpt-6.1-sol", "default"), "default")

    def test_flex_costs_include_cache_writes_and_long_context(self):
        for model, expected in (("gpt-6.1-sol", "0.260000"), ("gpt-6-luna", "0.014000")):
            with self.subTest(model=model):
                response = {"model": model, "service_tier": "flex", "usage": {
                    "input_tokens": 300000, "input_tokens_details": {"cached_tokens": 200000, "cache_write_tokens": 50000},
                    "output_tokens": 2000}}
                cost = response_usage_defaults(response)
                self.assertTrue(cost["long_context"])
                self.assertEqual(cost["estimated_cost_usd"], Decimal(expected))
                self.assertIn(model, cost["pricing_source"])
