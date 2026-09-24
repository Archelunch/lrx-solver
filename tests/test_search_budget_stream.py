"""Offline xAI SSE buffering and budget-fail-stop checks."""

import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from integrations.research_budget import Broker, BrokerHandler, DurableBudget, _buffer_chat_stream


def _sse_events(*events):
    return b"".join(b"data: " + json.dumps(event).encode() + b"\n\n"
                    for event in events) + b"data: [DONE]\n\n"


class StreamTests(unittest.TestCase):
    def test_stream_buffers_reasoning_content_and_final_usage(self):
        first = {"id": "sample", "model": "grok-4.7", "choices": [
            {"delta": {"role": "assistant", "reasoning_content": "thinking"}}]}
        second = {"choices": [{"delta": {"content": "```python\npass\n```"},
                               "finish_reason": "stop"}]}
        usage = {"choices": [], "usage": {"prompt_tokens": 10,
                 "completion_tokens": 5,
                 "completion_tokens_details": {"reasoning_tokens": 7}}}
        raw = _sse_events(first, second, usage)
        progress = {"response_bytes": 0, "event_count": 0,
                    "reasoning_chars": 0, "content_chars": 0, "events": []}
        result = _buffer_chat_stream(lambda: io.BytesIO(raw), deadline_seconds=1,
                                     max_bytes=10000, started=time.monotonic(),
                                     progress=progress)
        self.assertEqual(result["choices"][0]["message"]["content"], "```python\npass\n```")
        self.assertEqual(result["choices"][0]["finish_reason"], "stop")
        self.assertEqual(result["usage"]["completion_tokens_details"]["reasoning_tokens"], 7)
        self.assertEqual(progress["event_count"], 3)
        self.assertEqual(progress["response_bytes"], len(raw))
        self.assertIsNotNone(progress["first_reasoning_seconds"])
        self.assertIsNotNone(progress["first_content_seconds"])
        self.assertIsNotNone(progress["done_seconds"])

    def test_stream_deadline_preserves_partial_progress(self):
        first = _sse_events({"choices": [{"delta": {"reasoning_content": "started"}}]})

        class StalledStream(io.BytesIO):
            def readline(self, *args):
                line = super().readline(*args)
                if not line:
                    time.sleep(0.2)
                return line

        progress = {"response_bytes": 0, "event_count": 0,
                    "reasoning_chars": 0, "content_chars": 0, "events": []}
        with self.assertRaises(TimeoutError):
            _buffer_chat_stream(lambda: StalledStream(first[:-14]),
                                deadline_seconds=0.03, max_bytes=10000,
                                started=time.monotonic(), progress=progress)
        self.assertEqual(progress["event_count"], 1)
        self.assertEqual(progress["reasoning_chars"], 7)

    def test_stream_without_final_usage_is_not_accepted(self):
        raw = _sse_events({"choices": [{"delta": {"content": "draft"},
                                         "finish_reason": "stop"}]})
        progress = {"response_bytes": 0, "event_count": 0,
                    "reasoning_chars": 0, "content_chars": 0, "events": []}
        with self.assertRaisesRegex(ValueError, "final usage"):
            _buffer_chat_stream(lambda: io.BytesIO(raw), deadline_seconds=1,
                                max_bytes=10000, started=time.monotonic(),
                                progress=progress)
        self.assertEqual(progress["content_chars"], 5)

    def test_early_usage_does_not_substitute_for_final_usage(self):
        raw = _sse_events(
            {"choices": [{"delta": {"content": "draft"}}],
             "usage": {"prompt_tokens": 10, "completion_tokens": 1}},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]})
        progress = {"response_bytes": 0, "event_count": 0,
                    "reasoning_chars": 0, "content_chars": 0, "events": []}
        with self.assertRaisesRegex(ValueError, "final usage"):
            _buffer_chat_stream(lambda: io.BytesIO(raw), deadline_seconds=1,
                                max_bytes=10000, started=time.monotonic(),
                                progress=progress)
        self.assertEqual(progress["event_count"], 2)

    def test_native_json_client_gets_buffered_upstream_sse(self):
        raw = _sse_events(
            {"model": "grok-4.7", "choices": [{"delta": {"role": "assistant", "content": "word"},
                                                "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                                      "completion_tokens_details": {"reasoning_tokens": 7}}})

        class FakeOpener:
            def open(self, request, timeout):
                payload = json.loads(request.data)
                assert payload["stream"] is True
                assert payload["stream_options"] == {"include_usage": True}
                return io.BytesIO(raw)

        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableBudget(Path(directory) / "ledger.json", max_requests=1,
                                   max_usd=1, input_rate=1, output_rate=1)
            with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
                server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                                model="grok-4.7", api_key_env="TEST_RESEARCH_KEY", ledger=ledger,
                                max_tokens=100, reasoning_reserve=20, timeout=1,
                                upstream_stream=True)
            body = json.dumps({"model": "grok-4.7", "messages": [
                {"role": "user", "content": "find LRX word"}],
                "max_tokens": 20, "reasoning_effort": "low"}).encode()
            handler = object.__new__(BrokerHandler)
            handler.server = server
            handler.path = "/v1/chat/completions"
            handler.headers = {"Content-Length": str(len(body)),
                               "X-LRX-Call-Role": "gepa_preflight"}
            handler.rfile = io.BytesIO(body)
            handler.wfile = io.BytesIO()
            handler.request_version = "HTTP/1.1"
            handler.requestline = "POST /v1/chat/completions HTTP/1.1"
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            response = handler.wfile.getvalue()
            self.assertIn(b"200 OK", response)
            self.assertIn(b'"content": "word"', response)
            attempt = ledger.snapshot()["attempts"][0]
            receipt = json.loads(Path(attempt["receipt_path"]).read_text())
            self.assertEqual(attempt["status"], "ok")
            self.assertEqual(attempt["output_tokens"], 12)
            self.assertEqual(receipt["stream_progress"]["event_count"], 2)
            self.assertIsNotNone(receipt["stream_progress"]["headers_seconds"])
            self.assertIsNotNone(receipt["stream_progress"]["first_event_seconds"])
            self.assertIsNotNone(receipt["stream_progress"]["first_content_seconds"])
            self.assertIsNotNone(receipt["stream_progress"]["done_seconds"])
            self.assertEqual(receipt["finish_reason"], "stop")
            self.assertNotIn("stream", receipt["request_payload"])
            self.assertTrue(receipt["forwarded_request_payload"]["stream"])
            self.assertEqual(receipt["forwarded_request_payload"]["max_completion_tokens"], 20)
            ledger.close()


if __name__ == "__main__":
    unittest.main()
