"""Offline mock-HTTP tests for the reasoning-cap-enforced Grok transport.

Covers the lift-m9-260924 broker changes: a request whose reasoning exceeds
the configured cap is aborted and charged at (never above) its reservation;
durable partial receipts survive a stream that dies mid-way; a normal
response under cap is accepted and charged from terminal usage; the wall
timeout still fires and is recorded; and the forwarded payload carries the
enforced cap parameters. No network access; everything runs against fakes.
"""

import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.research_budget import (
    Broker, BrokerHandler, DurableBudget, _buffer_chat_stream)


def _sse_events(*events):
    return b"".join(b"data: " + json.dumps(event).encode() + b"\n\n"
                    for event in events) + b"data: [DONE]\n\n"


def _new_progress():
    return {"response_bytes": 0, "event_count": 0, "reasoning_chars": 0,
            "content_chars": 0, "events": []}


def _handler_for(directory, *, reasoning_cap_tokens=None, reasoning_effort="low",
                 timeout=1, max_tokens=100):
    ledger = DurableBudget(Path(directory) / "ledger.json", max_requests=2,
                           max_usd=10, input_rate=1, output_rate=1)
    with patch("integrations.research_budget.HTTPServer.__init__", return_value=None):
        server = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                        model="grok-4.7", api_key_env="TEST_RESEARCH_KEY", ledger=ledger,
                        max_tokens=max_tokens, reasoning_reserve=8000, timeout=timeout,
                        upstream_stream=True, reasoning_effort=reasoning_effort,
                        reasoning_cap_tokens=reasoning_cap_tokens)
    return ledger, server


def _post(server, body, *, role="gepa_reflection"):
    handler = object.__new__(BrokerHandler)
    handler.server = server
    handler.path = "/v1/chat/completions"
    handler.headers = {"Content-Length": str(len(body)), "X-LRX-Call-Role": role}
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.request_version = "HTTP/1.1"
    handler.requestline = "POST /v1/chat/completions HTTP/1.1"
    return handler


class TransportCapTests(unittest.TestCase):
    def test_reasoning_over_cap_is_fail_stopped_and_charged_at_reservation(self):
        # cap = 5 tokens -> 15 chars (see _CONSERVATIVE_CHARS_PER_REASONING_TOKEN);
        # the reasoning below crosses that well before any [DONE].
        raw = _sse_events(
            {"choices": [{"delta": {"role": "assistant",
                                    "reasoning_content": "this is much longer than the cap"}}]},
            {"choices": [{"delta": {"content": "unreachable"}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 1}})

        class FakeOpener:
            def open(self, request, timeout):
                return io.BytesIO(raw)

        with tempfile.TemporaryDirectory() as directory:
            ledger, server = _handler_for(directory, reasoning_cap_tokens=5)
            body = json.dumps({"model": "grok-4.7", "messages": [
                {"role": "user", "content": "find LRX word"}], "max_tokens": 20}).encode()
            handler = _post(server, body)
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            self.assertIn(b"502", handler.wfile.getvalue())
            attempt = ledger.snapshot()["attempts"][0]
            self.assertEqual(attempt["status"], "upstream_error")
            self.assertEqual(attempt["charged_usd"], attempt["reserved_usd"])
            self.assertFalse(attempt.get("reservation_overrun", False))
            receipt = json.loads(Path(attempt["receipt_path"]).read_text())
            self.assertEqual(receipt["error_type"], "ValueError")
            self.assertIsNotNone(receipt["stream_progress"]["reasoning_cap_exceeded_seconds"])
            ledger.close()

    def test_partial_receipts_persist_when_stream_dies_mid_way(self):
        first = _sse_events({"choices": [{"delta": {"reasoning_content": "started"}}]})

        class StalledStream(io.BytesIO):
            def readline(self, *args):
                line = super().readline(*args)
                if not line:
                    time.sleep(0.2)
                return line

        with tempfile.TemporaryDirectory() as directory:
            jsonl_path = Path(directory) / "attempt-0001.jsonl"
            progress = _new_progress()
            with self.assertRaises(TimeoutError):
                _buffer_chat_stream(lambda: StalledStream(first[:-14]),
                                    deadline_seconds=0.03, max_bytes=10000,
                                    started=time.monotonic(), progress=progress,
                                    jsonl_path=jsonl_path)
            self.assertTrue(jsonl_path.exists())
            records = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
            events = [r["event"] for r in records]
            self.assertIn("headers", events)
            self.assertIn("first_reasoning", events)
            self.assertIn("cancelled", events)
            self.assertIsNotNone(progress["cancelled_seconds"])

    def test_normal_response_under_cap_is_accepted_and_charged_from_usage(self):
        raw = _sse_events(
            {"choices": [{"delta": {"role": "assistant", "reasoning_content": "ok"}}]},
            {"choices": [{"delta": {"content": "word"}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                                      "completion_tokens_details": {"reasoning_tokens": 1}}})

        class FakeOpener:
            def open(self, request, timeout):
                return io.BytesIO(raw)

        with tempfile.TemporaryDirectory() as directory:
            ledger, server = _handler_for(directory, reasoning_cap_tokens=8000)
            body = json.dumps({"model": "grok-4.7", "messages": [
                {"role": "user", "content": "find LRX word"}], "max_tokens": 20}).encode()
            handler = _post(server, body)
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            self.assertIn(b"200 OK", handler.wfile.getvalue())
            attempt = ledger.snapshot()["attempts"][0]
            self.assertEqual(attempt["status"], "ok")
            self.assertEqual(attempt["input_tokens"], 10)
            self.assertEqual(attempt["output_tokens"], 6)
            self.assertAlmostEqual(attempt["charged_usd"], (10 + 6) / 1_000_000)
            receipt = json.loads(Path(attempt["receipt_path"]).read_text())
            jsonl_path = Path(attempt["receipt_path"]).with_suffix(".jsonl")
            self.assertTrue(jsonl_path.exists())
            terminal = [json.loads(line) for line in jsonl_path.read_text().splitlines()
                       if json.loads(line)["event"] == "terminal_usage"]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["finish_reason"], "stop")
            ledger.close()

    def test_wall_timeout_triggers_and_is_recorded(self):
        first = _sse_events({"choices": [{"delta": {"content": "partial"}}]})

        class StalledStream(io.BytesIO):
            def readline(self, *args):
                line = super().readline(*args)
                if not line:
                    time.sleep(1.5)
                return line

        class FakeOpener:
            def open(self, request, timeout):
                return StalledStream(first[:-14])

        with tempfile.TemporaryDirectory() as directory:
            # Broker.timeout must be a positive int; the stall (1.5s) exceeds
            # it so the 1s wall deadline fires first.
            ledger, server = _handler_for(directory, reasoning_cap_tokens=8000, timeout=1)
            body = json.dumps({"model": "grok-4.7", "messages": [
                {"role": "user", "content": "find LRX word"}], "max_tokens": 20}).encode()
            handler = _post(server, body)
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            self.assertIn(b"502", handler.wfile.getvalue())
            attempt = ledger.snapshot()["attempts"][0]
            self.assertEqual(attempt["status"], "upstream_error")
            self.assertEqual(attempt["charged_usd"], attempt["reserved_usd"])
            receipt = json.loads(Path(attempt["receipt_path"]).read_text())
            self.assertEqual(receipt["error_type"], "TimeoutError")
            self.assertIsNotNone(receipt["stream_progress"]["cancelled_seconds"])
            ledger.close()

    def test_forwarded_payload_carries_cap_parameters(self):
        raw = _sse_events(
            {"choices": [{"delta": {"role": "assistant", "content": "word"},
                          "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

        class FakeOpener:
            def open(self, request, timeout):
                payload = json.loads(request.data)
                assert payload["reasoning_effort"] == "low"
                assert payload["max_completion_tokens"] == 20
                return io.BytesIO(raw)

        with tempfile.TemporaryDirectory() as directory:
            ledger, server = _handler_for(directory, reasoning_cap_tokens=8000)
            # Client asks for "high"; the broker must force "low" regardless.
            body = json.dumps({"model": "grok-4.7", "messages": [
                {"role": "user", "content": "find LRX word"}],
                "max_tokens": 20, "reasoning_effort": "high"}).encode()
            handler = _post(server, body)
            with patch.dict(os.environ, {"TEST_RESEARCH_KEY": "offline-secret"}), \
                 patch("urllib.request.build_opener", return_value=FakeOpener()):
                handler.do_POST()
            self.assertIn(b"200 OK", handler.wfile.getvalue())
            attempt = ledger.snapshot()["attempts"][0]
            receipt = json.loads(Path(attempt["receipt_path"]).read_text())
            self.assertEqual(receipt["request_payload"]["reasoning_effort"], "high")
            self.assertEqual(receipt["forwarded_request_payload"]["reasoning_effort"], "low")
            self.assertEqual(receipt["forwarded_request_payload"]["max_completion_tokens"], 20)
            ledger.close()


if __name__ == "__main__":
    unittest.main()
