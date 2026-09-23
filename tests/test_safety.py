"""Regressions for bounded search, actual feedback, and mocked API safety."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.lrx.candidate_runner import run_experiment, parse_policy, DEFAULT_POLICY
from src.lrx.provider_adapter import BudgetLedger, XAIAdapter, _NoRedirectHandler
from tests.test_provider_adapter import _good_api_response, _mock_opener, _mock_response


class SearchSafety(unittest.TestCase):
    def test_invalid_json_not_silently_replaced_with_default(self):
        class Invalid:
            def propose(self, m, r, count):
                return ['{"weights": "wrong"}']

        result = run_experiment(2, 1, [(2, 1, 0)], proposer=Invalid(), proposals=1)
        self.assertEqual(result["failures"], 1)
        self.assertEqual(result["solved"], 0)
        for value in ["[]", "null", "true", "1", '{"a":1}']:
            with self.assertRaises(ValueError):
                parse_policy(value)

    def test_empty_word_preserved_in_logs(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "root.jsonl"
            result = run_experiment(2, 1, mode="parallel", proposals=2, output_file=out)
            self.assertEqual(result["results"][0]["word_length"], 0)
            for line in out.read_text().splitlines():
                self.assertEqual(json.loads(line)["word"], "")

    def test_sequential_receives_real_parent_and_feedback(self):
        class Spy:
            calls = []

            def propose_policy(self, m, r, parent, feedback, seed):
                self.calls.append((parent, feedback))
                return DEFAULT_POLICY

        spy = Spy()
        run_experiment(2, 1, [(2, 1, 0)], mode="sequential", proposals=3, proposer=spy)
        self.assertEqual(len(spy.calls), 3)
        self.assertIsNone(spy.calls[0][0])
        self.assertEqual(spy.calls[1][0], DEFAULT_POLICY)
        self.assertEqual(spy.calls[1][1]["result"], "SOLVED")

    def test_parallel_order_and_budget_are_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            outputs = []
            for i in range(2):
                p = Path(d) / f"{i}.jsonl"
                result = run_experiment(
                    3,
                    2,
                    [(3, 2, 1, 0, 0)],
                    mode="parallel",
                    proposals=8,
                    seed=9,
                    max_work=32,
                    output_file=p,
                )
                self.assertLessEqual(result["expansions"], 32)
                outputs.append(p.read_text())
            self.assertEqual(outputs[0], outputs[1])

    def test_inputs_are_rejected_before_search(self):
        for states in [[], [(1, 1, 0)], [(1, 2, 3)]]:
            with self.assertRaises(ValueError):
                run_experiment(2, 1, states)
        for count in [0, True, 101, 1.5]:
            with self.assertRaises(ValueError):
                run_experiment(2, 1, proposals=count)


class ProviderSafety(unittest.TestCase):
    def adapter(self, **kwargs):
        adapter = XAIAdapter(allow_network=True, **kwargs)
        adapter.attach_ledger(BudgetLedger(1, 1, 2))
        return adapter

    def test_finite_rates_and_limits_required(self):
        for value in [float("nan"), float("inf"), True, -1, 0]:
            with self.assertRaises(ValueError):
                BudgetLedger(value, 1, 2)
            with self.assertRaises(ValueError):
                BudgetLedger(1, value, 2)
        for kwargs in [
            {"timeout_sec": -1},
            {"max_response_bytes": -1},
            {"allow_network": "true"},
            {"max_requests": 0},
        ]:
            with self.assertRaises(ValueError):
                XAIAdapter(**kwargs)

    def test_pending_reservation_cannot_be_overwritten(self):
        ledger = BudgetLedger(1, 1, 2)
        ledger.reserve(100, 100)
        with self.assertRaises(RuntimeError):
            ledger.reserve(100, 100)
        ledger.charge_reservation()
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {"XAI_API_KEY": "dummy-only"})
    @patch("urllib.request.build_opener")
    def test_runner_uses_adapter_and_accounts_usage(self, build):
        build.return_value = _mock_opener(_mock_response(_good_api_response()))
        adapter = self.adapter()
        result = run_experiment(
            2, 1, [(2, 1, 0)], proposals=2, mode="sequential", proposer=adapter
        )
        self.assertEqual(result["solved"], 1)
        self.assertEqual(result["model_usage"]["requests"], 2)
        self.assertEqual(result["model_usage"]["input_tokens"], 160)
        self.assertNotIn("dummy-only", json.dumps(result))

    @patch.dict("os.environ", {"XAI_API_KEY": "dummy-only"})
    @patch("urllib.request.build_opener")
    def test_oversize_response_and_bad_usage_keep_reservations(self, build):
        adapter = self.adapter(max_response_bytes=8, max_requests=1)
        build.return_value = _mock_opener(_mock_response(_good_api_response()))
        with self.assertRaises(ValueError):
            adapter.propose(2, 1)
        self.assertGreater(adapter.usage()["estimated_usd"], 0)
        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)
        with self.assertRaises(RuntimeError):
            adapter.attach_ledger(BudgetLedger(2, 1, 2))

    @patch.dict("os.environ", {"XAI_API_KEY": "dummy-only"})
    @patch("urllib.request.build_opener")
    def test_over_cap_provider_usage_stops_campaign(self, build):
        data = _good_api_response()
        data["usage"]["completion_tokens"] = 201
        build.return_value = _mock_opener(_mock_response(data))
        adapter = self.adapter(max_output_tokens=200)
        with self.assertRaises(ValueError):
            adapter.propose(2, 1)
        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)
        self.assertEqual(adapter.usage()["output_tokens"], 201)

    def test_prompt_not_truncated_silently(self):
        adapter = self.adapter(max_prompt_bytes=1)
        with self.assertRaises(ValueError):
            adapter.propose(2, 1)
        self.assertEqual(adapter.usage()["requests"], 0)

    def test_real_redirect_handler_refuses(self):
        import urllib.error

        with self.assertRaises(urllib.error.URLError):
            _NoRedirectHandler().redirect_request(
                None, None, 308, None, {}, "https://other.example/"
            )
