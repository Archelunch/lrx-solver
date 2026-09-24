"""Focused offline checks for the official research harness boundary."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.research_archive import DevelopmentArchive
from integrations.research_budget import Broker, BrokerHandler, BudgetExceeded, DurableBudget


class BudgetTests(unittest.TestCase):
    def budget(self, path, max_requests=2):
        return DurableBudget(path, max_requests=max_requests, max_usd=1,
                             input_rate=1, output_rate=1)

    def test_failed_and_reflection_calls_share_durable_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ledger.json"
            ledger = self.budget(path)
            first = ledger.reserve(100, 100, kind="proposal")
            ledger.settle(first, usage={"prompt_tokens": 100, "completion_tokens": 100})
            second = ledger.reserve(100, 100, kind="reflection")
            self.assertEqual(second, 2)
            ledger.close()
            resumed = self.budget(path)
            with self.assertRaises(BudgetExceeded):
                resumed.reserve(100, 100, kind="meta")
            self.assertEqual([a["status"] for a in resumed.snapshot()["attempts"]],
                             ["ok", "reserved"])
            resumed.close()

    def test_error_and_unknown_usage_halt_restarted_ledger(self):
        for failure in ("upstream_error", "missing_usage"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "ledger.json"
                ledger = self.budget(path)
                call = ledger.reserve(10, 10)
                ledger.settle(call, status=failure)
                ledger.close()
                with self.assertRaises(BudgetExceeded):
                    self.budget(path).reserve(10, 10)

    def test_missing_usage_halts_and_live_second_owner_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ledger.json"
            ledger = self.budget(path)
            with self.assertRaisesRegex(RuntimeError, "live broker owner"):
                self.budget(path)
            call = ledger.reserve(10, 10)
            self.assertEqual(ledger.settle(call)["status"], "missing_usage")
            ledger.close()
            resumed = self.budget(path)
            with self.assertRaises(BudgetExceeded):
                resumed.reserve(10, 10)
            resumed.close()

    def test_nonfinite_limit_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in (float("nan"), float("inf")):
                with self.assertRaises(ValueError):
                    DurableBudget(Path(folder) / "ledger.json", max_requests=1,
                                  max_usd=value, input_rate=1, output_rate=1)

    def test_dollar_reservation_and_usage_overrun(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = DurableBudget(Path(folder) / "ledger.json", max_requests=3,
                                   max_usd=.002, input_rate=1, output_rate=1)
            with self.assertRaises(BudgetExceeded):
                ledger.reserve(100, 1000)
            self.assertEqual(ledger.snapshot()["attempts"], [])
            call = ledger.reserve(100, 100)
            settled = ledger.settle(call, usage={"prompt_tokens": 200,
                                                 "completion_tokens": 3000})
            self.assertTrue(settled["reservation_overrun"])
            with self.assertRaises(BudgetExceeded):
                ledger.reserve(10, 10)

    def test_broker_mock_upstream_and_cap(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, *_):
                return json.dumps({"choices": [{"message": {"content": "ok"}}],
                                   "usage": {"prompt_tokens": 10,
                                             "completion_tokens": 4}}).encode()

        class FakeOpener:
            def open(self, request, timeout):
                self_url = request.full_url
                assert self_url == "https://api.example.com/v1/chat/completions"
                assert request.get_header("Authorization") == "Bearer secret"
                return FakeResponse()

        with tempfile.TemporaryDirectory() as folder:
            ledger = self.budget(Path(folder) / "ledger.json", max_requests=1)
            with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
                server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                                model="model", api_key_env="TEST_RESEARCH_KEY", ledger=ledger,
                                max_tokens=100, reasoning_reserve=100)
            body = json.dumps({"model": "model", "messages": [{"role": "user",
                "content": "test"}], "max_tokens": 20}).encode()

            def invoke():
                handler = object.__new__(BrokerHandler)
                handler.server = server
                handler.path = "/v1/chat/completions"
                handler.headers = {"Content-Length": str(len(body))}
                handler.rfile = io.BytesIO(body)
                handler.wfile = io.BytesIO()
                handler.request_version = "HTTP/1.1"
                handler.requestline = "POST /v1/chat/completions HTTP/1.1"
                handler.do_POST()
                return handler.wfile.getvalue()

            with patch.dict("os.environ", {"TEST_RESEARCH_KEY": "secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                first = invoke()
                self.assertIn(b"200 OK", first)
                self.assertIn(b'"content": "ok"', first)
                second = invoke()
                self.assertIn(b"429 Too Many Requests", second)
            self.assertEqual(len(ledger.snapshot()["attempts"]), 1)

    def test_rejects_multi_completion_and_unknown_token_override(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = self.budget(Path(folder) / "ledger.json")
            with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
                server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                                model="model", api_key_env="TEST_RESEARCH_KEY", ledger=ledger)
            for extra in ({"n": 2}, {"max_output_tokens": 999999}):
                body = json.dumps(dict(model="model", messages=[{"role": "user",
                    "content": "x"}], max_tokens=20, **extra)).encode()
                handler = object.__new__(BrokerHandler)
                handler.server = server
                handler.path = "/v1/chat/completions"
                handler.headers = {"Content-Length": str(len(body))}
                handler.rfile = io.BytesIO(body)
                handler.wfile = io.BytesIO()
                handler.request_version = "HTTP/1.1"
                handler.requestline = "POST /v1/chat/completions HTTP/1.1"
                handler.do_POST()
                self.assertIn(b"400 Bad Request", handler.wfile.getvalue())
            self.assertEqual(ledger.snapshot()["attempts"], [])


class ArchiveTests(unittest.TestCase):
    def test_development_trace_diff_query_and_confirmation_exclusion(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = DevelopmentArchive(Path(folder) / "archive.sqlite")
            first = archive.add(run_id="gepa-a", engine="gepa", source="def f():\n  return 1\n",
                                score=0, feedback={"miss": "block 7"},
                                traces=[{"word": "LX", "base": 2, "gamma": [4]}],
                                provenance={"dataset_sha256": "abc"})
            child = archive.add(run_id="gepa-a", engine="gepa", parent_id=first,
                                source="def f():\n  return 2\n", score=1,
                                feedback={"certified": 1},
                                traces=[{"word": "RX", "base": 2, "gamma": [5]}],
                                provenance={"dataset_sha256": "abc"})
            self.assertIn("+  return 2", archive.get(child)["source_diff"])
            self.assertEqual(archive.search("RX")[0]["id"], child)
            self.assertEqual(archive.search("block 7")[0]["id"], first)
            with self.assertRaises(ValueError):
                archive.add(run_id="confirm", engine="gepa", source="x", score=1,
                            feedback={}, traces=[], provenance={}, split="confirmation")
            archive.close()


if __name__ == "__main__":
    unittest.main()
