"""Offline receipt checks for the durable official model broker."""

import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.research_budget import Broker, BrokerHandler, DurableBudget


class ReceiptTests(unittest.TestCase):
    def _simulate(self, directory, raw, *, disconnect=False):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, *_args):
                return raw

        class FakeOpener:
            def open(self, request, timeout):
                return FakeResponse()

        class BrokenBodyStream(io.BytesIO):
            def write(self, data):
                if disconnect and data.startswith(b'{"choices"'):
                    raise BrokenPipeError("downstream closed")
                return super().write(data)

        ledger = DurableBudget(Path(directory) / "ledger.json", max_requests=1,
                               max_usd=1, input_rate=1, output_rate=1)
        with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
            server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                            model="grok-4.7", api_key_env="TEST_RESEARCH_KEY", ledger=ledger,
                            max_tokens=100, reasoning_reserve=0)
        body = json.dumps({"model": "grok-4.7", "messages": [{"role": "user", "content": "math"}],
                           "max_tokens": 20}).encode()
        handler = object.__new__(BrokerHandler)
        handler.server = server
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = BrokenBodyStream()
        handler.request_version = "HTTP/1.1"
        handler.requestline = "POST /v1/chat/completions HTTP/1.1"
        with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
             patch("urllib.request.build_opener", return_value=FakeOpener()):
            handler.do_POST()
        attempt = ledger.snapshot()["attempts"][0]
        receipt = json.loads(Path(attempt["receipt_path"]).read_text())
        ledger.close()
        return attempt, receipt

    def test_full_sanitized_response_and_request_are_private_and_auditable(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, *_args):
                return json.dumps({
                    "model": "grok-4.7",
                    "choices": [{"finish_reason": "length", "message": {
                        "role": "assistant", "content": "```python\npass\n``` xai-ABCDEFGHIJKLMNO"}}],
                    "usage": {"prompt_tokens": 40, "completion_tokens": 10},
                }).encode()

        class FakeOpener:
            def open(self, request, timeout):
                self_request = json.loads(request.data)
                assert self_request["messages"][0]["content"].startswith("secret")
                return FakeResponse()

        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableBudget(Path(directory) / "ledger.json", max_requests=1,
                                   max_usd=1, input_rate=1, output_rate=1)
            with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
                server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                                model="grok-4.7", api_key_env="TEST_RESEARCH_KEY", ledger=ledger,
                                max_tokens=100, reasoning_reserve=0)
            body = json.dumps({"model": "grok-4.7", "messages": [{"role": "user",
                "content": "secret prompt with exact mathematics"}], "max_tokens": 20}).encode()
            handler = object.__new__(BrokerHandler)
            handler.server = server
            handler.path = "/v1/chat/completions"
            handler.headers = {"Content-Length": str(len(body)),
                               "X-LRX-Call-Role": "gepa_reflection",
                               "X-LRX-Context-SHA256": "a" * 64,
                               "X-LRX-Archive-Ids": "7,12"}
            handler.rfile = io.BytesIO(body)
            handler.wfile = io.BytesIO()
            handler.request_version = "HTTP/1.1"
            handler.requestline = "POST /v1/chat/completions HTTP/1.1"
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            self.assertIn(b"200 OK", handler.wfile.getvalue())
            attempt = ledger.snapshot()["attempts"][0]
            receipt_path = Path(attempt["receipt_path"])
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(stat.S_IMODE(receipt_path.stat().st_mode), 0o600)
            self.assertEqual(receipt["role"], "gepa_reflection")
            self.assertEqual(receipt["declared_context_sha256"], "a" * 64)
            self.assertEqual(receipt["declared_archive_ids"], [7, 12])
            self.assertEqual(receipt["response_role"], "assistant")
            self.assertEqual(receipt["finish_reason"], "length")
            self.assertGreaterEqual(receipt["latency_seconds"], 0)
            self.assertIn("exact mathematics", receipt["request_payload"]["messages"][0]["content"])
            self.assertNotIn("secret", receipt_path.read_text())
            self.assertNotIn("xai-ABCDEFGHIJKLMNO", receipt_path.read_text())
            ledger.close()

    def test_malformed_upstream_body_is_preserved_and_charged_conservatively(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt, receipt = self._simulate(directory, b"broken upstream offline-secret")
            self.assertEqual(attempt["status"], "upstream_error")
            self.assertEqual(receipt["response_payload"], "broken upstream [REDACTED_CREDENTIAL]")
            self.assertEqual(receipt["response_status"], 502)

    def test_downstream_disconnect_does_not_erase_settled_provider_receipt(self):
        raw = json.dumps({"choices": [{"finish_reason": "stop", "message": {
            "role": "assistant", "content": "complete source"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}).encode()
        with tempfile.TemporaryDirectory() as directory:
            attempt, receipt = self._simulate(directory, raw, disconnect=True)
            self.assertEqual(attempt["status"], "ok")
            self.assertEqual(receipt["response_payload"]["choices"][0]["message"]["content"],
                             "complete source")
            self.assertEqual(receipt["finish_reason"], "stop")
            self.assertEqual(receipt["broker_status"], 200)


if __name__ == "__main__":
    unittest.main()
