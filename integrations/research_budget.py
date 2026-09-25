"""Local OpenAI chat broker with one durable request and estimated-spend cap.

The broker owns the upstream credential. Bind only to loopback and give official
engines its /v1 URL and a dummy local API key. Every forwarded attempt consumes
one request slot; an error or missing usage consumes its whole reservation.
"""

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from src.lrx.provider_adapter import _NoRedirectHandler, _validate_https_url


class BudgetExceeded(RuntimeError):
    pass


_SECRET_PATTERN = re.compile(r"(?i)\b(?:bearer\s+|xai-|sk-)[A-Za-z0-9._-]{12,}")
_SECRET_KEYS = frozenset(("api_key", "access_token", "authorization", "secret", "password"))
_CALL_ROLES = frozenset(("gepa_reflection", "gepa_preflight", "sky_solution",
                         "sky_meta", "sky_variation", "unknown"))

# xAI docs (developers/model-capabilities/text/reasoning, fetched 2026-09-24)
# document `reasoning_effort` for grok-4.7 as one of these levels; there is no
# documented numeric reasoning-token cap parameter. See
# autoresearch/lift-m9-260924/transport-notes.md.
_REASONING_EFFORTS = frozenset(("low", "medium", "high", "xhigh"))

# No per-chunk reasoning token count is available from the SSE delta stream,
# only cumulative reasoning characters. This ratio is a deliberately
# conservative (small) chars-per-token estimate so the local abort fires at
# or before the configured reasoning_cap_tokens is actually reached; it is
# not a provider-documented figure. See transport-notes.md.
_CONSERVATIVE_CHARS_PER_REASONING_TOKEN = 3

# A wall-timeout cancel or upstream connection error is charged at the full
# reservation (never above it) and is retried up to this many times in a
# row before the broker halts; a reservation overrun or a post-response
# billing/credential/receipt problem still halts on the first occurrence.
_RETRYABLE_FAILURE = "upstream_error"
_MAX_CONSECUTIVE_FAILURES = 3

# Bounded in-slot retry for a transient upstream failure (502/503/504, or
# 429 with a Retry-After header): up to this many tries, all inside the one
# reservation and receipt already made for the call, charging only the
# final settled usage. A 4xx other than 429, a timeout, or any HTTPError
# received after streamed answer bytes already arrived (non-idempotent) is
# never retried here; it falls through to the existing single-shot
# consecutive-failure handling below.
_TRANSIENT_HTTP_CODES = (502, 503, 504)
_MAX_TRANSIENT_TRIES = 3
_TRANSIENT_BACKOFF_SECONDS = (2, 4, 8)


def _append_jsonl(path, record):
    """Append one durable record; survives a hard kill mid-stream (fsync)."""
    line = (json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)


def _sanitize(value, credential):
    """Retain complete audit text while removing credential-shaped substrings."""
    if isinstance(value, str):
        if credential:
            value = value.replace(credential, "[REDACTED_CREDENTIAL]")
        return _SECRET_PATTERN.sub("[REDACTED_TOKEN]", value)
    if isinstance(value, list):
        return [_sanitize(item, credential) for item in value]
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if str(key).lower() in _SECRET_KEYS
                      else _sanitize(item, credential)) for key, item in value.items()}
    return value


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _stream_snapshot(progress):
    """Copy fixed fields without iterating a reader-mutated mapping or list."""
    keys = ("headers_seconds", "first_event_seconds", "first_reasoning_seconds",
            "first_content_seconds", "done_seconds", "cancelled_seconds",
            "reasoning_cap_exceeded_seconds", "response_bytes", "event_count",
            "reasoning_chars", "content_chars")
    snapshot = {key: progress.get(key) for key in keys}
    snapshot["events"] = list(progress["events"])
    return snapshot


def _buffer_chat_stream(fetch, *, deadline_seconds, max_bytes, started, progress,
                        reasoning_char_cap=None, jsonl_path=None):
    """Read xAI SSE to a chat JSON response with a hard total wall deadline.

    The fetch runs in a daemon thread so a stalled header or SSE read cannot
    extend the budgeted attempt past the deadline. The broker fail-stops if a
    complete stream and its final usage are unavailable.

    If `reasoning_char_cap` is given, the read aborts as soon as cumulative
    reasoning characters exceed it (a conservative proxy for a reasoning
    token cap, since no provider-reported running token count exists
    mid-stream); the caller charges the reservation on abort, so no single
    request's actual spend can exceed what was reserved for it. If
    `jsonl_path` is given, timing/count milestones are appended durably
    (fsynced) as they happen, so a hard process kill mid-stream still leaves
    an audit trail.
    """
    outcome = {}
    stop = threading.Event()
    active_response = []

    def _mark(event, **fields):
        if jsonl_path is not None:
            record = {"event": event, "elapsed_seconds": time.monotonic() - started,
                      "chunk_count": progress["event_count"]}
            record.update(fields)
            _append_jsonl(jsonl_path, record)

    def read():
        try:
            response = fetch()
            active_response.append(response)
            with response:
                if stop.is_set():
                    return
                progress["headers_seconds"] = time.monotonic() - started
                _mark("headers")
                data_lines = []
                content = []
                role = "assistant"
                finish_reason = None
                usage = None
                last_event_had_usage = False
                identity = {}
                done = False

                def accept_event():
                    nonlocal role, finish_reason, usage, done, last_event_had_usage
                    if stop.is_set():
                        return
                    if not data_lines:
                        return
                    value = "\n".join(data_lines)
                    data_lines.clear()
                    if value == "[DONE]":
                        done = True
                        progress["done_seconds"] = time.monotonic() - started
                        _mark("done")
                        return
                    event = json.loads(value)
                    if not isinstance(event, dict):
                        raise ValueError("invalid SSE event")
                    progress["events"].append(event)
                    progress["event_count"] += 1
                    if progress.get("first_event_seconds") is None:
                        progress["first_event_seconds"] = time.monotonic() - started
                        _mark("first_event")
                    for key in ("id", "model", "created", "system_fingerprint"):
                        if key in event and key not in identity:
                            identity[key] = event[key]
                    last_event_had_usage = isinstance(event.get("usage"), dict)
                    if last_event_had_usage:
                        usage = event["usage"]
                    choices = event.get("choices")
                    if not isinstance(choices, list) or not choices:
                        return
                    first = choices[0]
                    if not isinstance(first, dict):
                        raise ValueError("invalid SSE choice")
                    delta = first.get("delta") or {}
                    if not isinstance(delta, dict):
                        raise ValueError("invalid SSE delta")
                    if isinstance(delta.get("role"), str):
                        role = delta["role"]
                    reasoning = delta.get("reasoning_content")
                    if isinstance(reasoning, str) and reasoning:
                        progress["reasoning_chars"] += len(reasoning)
                        if progress.get("first_reasoning_seconds") is None:
                            progress["first_reasoning_seconds"] = time.monotonic() - started
                            _mark("first_reasoning")
                        if (reasoning_char_cap is not None and
                                progress["reasoning_chars"] > reasoning_char_cap):
                            progress["reasoning_cap_exceeded_seconds"] = time.monotonic() - started
                            _mark("reasoning_cap_exceeded",
                                 reasoning_chars=progress["reasoning_chars"],
                                 reasoning_char_cap=reasoning_char_cap)
                            raise ValueError(
                                "reasoning cap exceeded; stream aborted before completion")
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        content.append(text)
                        progress["content_chars"] += len(text)
                        if progress.get("first_content_seconds") is None:
                            progress["first_content_seconds"] = time.monotonic() - started
                            _mark("first_content")
                    if first.get("finish_reason") is not None:
                        finish_reason = first["finish_reason"]

                while not done and not stop.is_set():
                    line = response.readline(max_bytes - progress["response_bytes"] + 1)
                    if stop.is_set():
                        break
                    if not line:
                        accept_event()
                        break
                    progress["response_bytes"] += len(line)
                    if progress["response_bytes"] > max_bytes:
                        raise ValueError("upstream response byte cap exceeded")
                    stripped = line.decode("utf-8").rstrip("\r\n")
                    if stripped.startswith("data:"):
                        data_lines.append(stripped[5:].lstrip())
                    elif not stripped:
                        accept_event()
                if stop.is_set():
                    # Cancelled by the caller's wall deadline; that path
                    # already records "cancelled" and raises TimeoutError in
                    # the main thread. Do not race it with a second error.
                    return
                if not done:
                    raise ValueError("stream ended without [DONE]")
                if not last_event_had_usage or not isinstance(usage, dict):
                    raise ValueError("stream ended without final usage")
                if finish_reason is None:
                    raise ValueError("stream ended without finish reason")
                outcome["result"] = {**identity, "object": "chat.completion",
                                     "choices": [{"index": 0, "message": {"role": role,
                                                                     "content": "".join(content)},
                                                  "finish_reason": finish_reason}],
                                     "usage": usage}
                _mark("terminal_usage", finish_reason=finish_reason, usage=usage)
        except BaseException as exc:
            outcome["error"] = exc
            if not stop.is_set():
                _mark("error", error_type=type(exc).__name__)

    worker = threading.Thread(target=read, daemon=True)
    worker.start()
    worker.join(max(0, deadline_seconds - (time.monotonic() - started)))
    if worker.is_alive():
        stop.set()
        if active_response:
            response = active_response[0]
            try:
                response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
            except (AttributeError, OSError):
                pass
            try:
                response.close()
            except OSError:
                pass
        worker.join(0.1)
        progress["cancelled_seconds"] = time.monotonic() - started
        _mark("cancelled")
        raise TimeoutError("stream total wall deadline exceeded")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


class DurableBudget:
    """Persist reservations before network I/O; restart charges unfinished calls."""

    def __init__(self, path, *, max_requests, max_usd, input_rate, output_rate):
        if type(max_requests) is not int or max_requests < 1:
            raise ValueError("max_requests must be positive")
        if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in
               (max_usd, input_rate, output_rate)):
            raise ValueError("max_usd and rates must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.receipts_dir = self.path.with_suffix(self.path.suffix + ".receipts")
        self.receipts_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.receipts_dir, 0o700)
        self._owner_file = self.path.with_suffix(self.path.suffix + ".owner")
        self._owner = self._owner_file.open("a+")
        try:
            fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._owner.close()
            raise RuntimeError("ledger already has a live broker owner") from None
        self.lock = threading.Lock()
        self.limits = dict(max_requests=max_requests, max_usd=float(max_usd),
                           input_rate=float(input_rate), output_rate=float(output_rate))
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            if self.state["limits"] != self.limits:
                raise ValueError("ledger limits changed; use a fresh ledger path")
        else:
            self.state = dict(limits=self.limits, attempts=[], spent_usd=0.0,
                              halted_reason=None, consecutive_failures=0)
            self._save()

    def close(self):
        if not self._owner.closed:
            fcntl.flock(self._owner.fileno(), fcntl.LOCK_UN)
            self._owner.close()

    def __del__(self):
        owner = getattr(self, "_owner", None)
        if owner is not None and not owner.closed:
            self.close()

    def _save(self):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w") as stream:
            json.dump(self.state, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, self.path)

    def reserve(self, prompt_bytes, output_tokens, *, kind="chat", role="unknown"):
        # UTF-8 byte count is deliberately larger than ordinary text token
        # counts; a fixed allowance covers chat framing. Reasoning allowance
        # is separate because some providers do not include it in max_tokens.
        worst_input = prompt_bytes + 1024
        worst_output = output_tokens
        reserved = (worst_input * self.limits["input_rate"] +
                    worst_output * self.limits["output_rate"]) / 1_000_000
        with self.lock:
            if self.state.get("halted_reason"):
                raise BudgetExceeded("broker halted: " + self.state["halted_reason"])
            if any(a["status"] == "reserved" for a in self.state["attempts"]):
                # A process restart cannot know whether a reserved call was
                # billed; refuse new calls until its receipt is reconciled.
                raise BudgetExceeded("unsettled upstream request")
            if len(self.state["attempts"]) >= self.limits["max_requests"]:
                raise BudgetExceeded("shared upstream request cap reached")
            if self.state["spent_usd"] + reserved > self.limits["max_usd"]:
                raise BudgetExceeded("shared estimated spend cap reached")
            attempt = dict(id=len(self.state["attempts"]) + 1, kind=kind, role=role,
                           reserved_usd=reserved, charged_usd=reserved,
                           status="reserved", input_tokens=None, output_tokens=None)
            self.state["attempts"].append(attempt)
            self.state["spent_usd"] += reserved
            self._save()
            return attempt["id"]

    def write_receipt(self, attempt_id, receipt):
        """Atomically persist the sanitized, complete request/response payload."""
        path = self.receipts_dir / f"attempt-{attempt_id:04d}.json"
        tmp = self.receipts_dir / f"attempt-{attempt_id:04d}.tmp"
        data = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        with self.lock:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp, path)
                self.state["attempts"][attempt_id - 1]["receipt_path"] = str(path)
                self._save()
            finally:
                if tmp.exists():
                    tmp.unlink()
        return path

    def settle(self, attempt_id, *, usage=None, status="ok"):
        with self.lock:
            attempt = self.state["attempts"][attempt_id - 1]
            if attempt["status"] != "reserved":
                raise ValueError("attempt already settled")
            actual = attempt["reserved_usd"]
            if usage is not None:
                tokens_in = usage.get("prompt_tokens")
                tokens_out = usage.get("completion_tokens")
                reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
                if all(type(x) is int and x >= 0 for x in (tokens_in, tokens_out, reasoning)):
                    # xAI reports reasoning separately; err on the high side
                    # if another provider already includes it in completion.
                    tokens_out += reasoning
                    actual = (tokens_in * self.limits["input_rate"] +
                              tokens_out * self.limits["output_rate"]) / 1_000_000
                    ticks = usage.get("cost_in_usd_ticks")
                    if type(ticks) is int and ticks >= 0:
                        actual = max(actual, ticks / 1e10)
                    attempt.update(input_tokens=tokens_in, output_tokens=tokens_out)
                else:
                    status = "missing_usage"
            elif status == "ok":
                status = "missing_usage"
            attempt["status"] = status
            attempt["charged_usd"] = actual
            attempt["reservation_overrun"] = actual > attempt["reserved_usd"]
            self.state["spent_usd"] += actual - attempt["reserved_usd"]
            if attempt["reservation_overrun"]:
                # Actual cost exceeded what was reserved: halt immediately,
                # regardless of status; billing trust is broken.
                self.state["halted_reason"] = "reservation overrun"
            elif status == "ok":
                self.state["consecutive_failures"] = 0
            elif status == _RETRYABLE_FAILURE:
                # A single wall-timeout cancel or upstream connection error
                # (already charged at the reservation, never above it) is
                # not itself fatal: GEPA/AdaEvolve/EvoX can try again. Only
                # halt after 3 in a row, so one slow provider response does
                # not kill the whole arm.
                self.state["consecutive_failures"] = self.state.get("consecutive_failures", 0) + 1
                if self.state["consecutive_failures"] >= _MAX_CONSECUTIVE_FAILURES:
                    self.state["halted_reason"] = (
                        f"{_MAX_CONSECUTIVE_FAILURES} consecutive {status} attempts")
            else:
                # missing_usage (billing became untrustworthy after a
                # response was actually received), missing_credential, and
                # receipt_error are not retried; halt immediately as before.
                self.state["halted_reason"] = status
            self._save()
            return attempt.copy()

    def resume(self, *, note, who="orchestrator"):
        """Clear a halt with an appended, permanent audit entry.

        Never hand-edit the ledger file: this is the only sanctioned way to
        un-halt it, and it can never touch attempts or spent_usd — a halted
        ledger's charged history is permanent.
        """
        if not note or not isinstance(note, str):
            raise ValueError("resume requires a non-empty note")
        with self.lock:
            if not self.state.get("halted_reason"):
                raise ValueError("ledger is not halted")
            entry = {"at_utc": _utc_now(), "who": who, "note": note,
                     "cleared_halted_reason": self.state["halted_reason"],
                     "consecutive_failures_before": self.state.get("consecutive_failures", 0),
                     "spent_usd_at_resume": self.state["spent_usd"]}
            self.state.setdefault("resume_log", []).append(entry)
            self.state["halted_reason"] = None
            self.state["consecutive_failures"] = 0
            self._save()
            return entry

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))


class Broker(HTTPServer):
    def __init__(self, address, *, upstream_url, model, api_key_env, ledger,
                 max_prompt_bytes=120_000, max_response_bytes=8_000_000,
                 max_tokens=4000, reasoning_reserve=20_000, timeout=180,
                 upstream_stream=False, reasoning_effort=None,
                 reasoning_cap_tokens=None, retry_transient=True):
        _validate_https_url(upstream_url)
        if not model or not api_key_env.isidentifier():
            raise ValueError("invalid model or credential variable")
        if any(type(x) is not int or x < 1 for x in
               (max_prompt_bytes, max_response_bytes, max_tokens, timeout)):
            raise ValueError("invalid positive limit")
        if type(reasoning_reserve) is not int or reasoning_reserve < 0:
            raise ValueError("invalid reasoning reserve")
        if reasoning_effort is not None and reasoning_effort not in _REASONING_EFFORTS:
            raise ValueError("invalid reasoning_effort")
        if reasoning_cap_tokens is not None and (
                type(reasoning_cap_tokens) is not int or reasoning_cap_tokens < 1):
            raise ValueError("invalid reasoning_cap_tokens")
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("broker may bind only to loopback")
        self.upstream_url = upstream_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.ledger = ledger
        # `reasoning_effort` is the only documented xAI knob and is enforced
        # (forced into every forwarded request, overriding any client
        # value); it is a hint, not a guaranteed numeric cap. When
        # `reasoning_cap_tokens` is set, the broker also aborts an
        # upstream-stream request in real time once cumulative reasoning
        # characters cross a conservative token-to-char estimate of that cap
        # (see transport-notes.md), which bounds actual charge at the
        # reservation regardless of what the provider ultimately reasons.
        self.reasoning_effort = reasoning_effort
        self.reasoning_cap_tokens = reasoning_cap_tokens
        self.max_prompt_bytes = max_prompt_bytes
        self.max_response_bytes = max_response_bytes
        self.max_tokens = max_tokens
        self.reasoning_reserve = reasoning_reserve
        self.timeout = timeout
        self.upstream_stream = upstream_stream
        # Covered by the existing reservation formula unchanged: retries
        # happen inside one already-reserved slot, never add a reservation.
        self.retry_transient = bool(retry_transient)
        super().__init__(address, BrokerHandler)


class BrokerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Never log request bodies, headers, or provider error bodies.
        return

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/v1/models":
            self._json(200, {"object": "list", "data": [{"id": self.server.model, "object": "model"}]})
        elif self.path == "/health":
            state = self.server.ledger.snapshot()
            self._json(200, {"requests": len(state["attempts"]),
                             "estimated_spent_usd": state["spent_usd"]})
        else:
            self._json(404, {"error": {"message": "unknown endpoint"}})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": {"message": "unknown endpoint"}})
            return
        request_started = time.monotonic()
        role = self.headers.get("X-LRX-Call-Role", "unknown")
        if role not in _CALL_ROLES:
            role = "unknown"
        context_hash = self.headers.get("X-LRX-Context-SHA256")
        if not (isinstance(context_hash, str) and len(context_hash) == 64 and
                all(c in "0123456789abcdef" for c in context_hash)):
            context_hash = None
        archive_ids_header = self.headers.get("X-LRX-Archive-Ids", "")[:256]
        archive_ids = [int(item) for item in archive_ids_header.split(",")
                       if item.isdigit()][:8]
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= self.server.max_prompt_bytes:
                raise ValueError("request byte cap exceeded")
            body = self.rfile.read(size)
            payload = json.loads(body)
            if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
                raise ValueError("chat messages required")
            accepted = {"model", "messages", "max_tokens", "max_completion_tokens",
                        "temperature", "top_p", "stop", "seed", "reasoning_effort",
                        "response_format", "stream", "stream_options", "n"}
            if set(payload) - accepted:
                raise ValueError("unsupported chat request fields")
            if payload.get("n", 1) != 1 or type(payload.get("n", 1)) is not int:
                raise ValueError("n must equal 1")
            if "max_tokens" in payload and "max_completion_tokens" in payload:
                raise ValueError("specify one output token bound")
            if type(payload.get("stream", False)) is not bool:
                raise ValueError("stream must be boolean")
            if payload.get("stream", False) or "stream_options" in payload:
                raise ValueError("client streaming is unsupported; use broker upstream-stream mode")
            if payload.get("tools") or payload.get("functions"):
                raise ValueError("tool calls are unsupported by the budget broker")
            output_tokens = payload.get("max_completion_tokens", payload.get("max_tokens"))
            if type(output_tokens) is not int or not 1 <= output_tokens <= self.server.max_tokens:
                raise ValueError("bounded max_tokens or max_completion_tokens required")
            if not all(isinstance(m, dict) and isinstance(m.get("content"), str)
                       for m in payload["messages"]):
                raise ValueError("text chat messages required")
            if payload.get("model") != self.server.model:
                raise ValueError("request model does not match broker model")
            streaming = self.server.upstream_stream
            wire_payload = dict(payload)
            if self.server.reasoning_effort is not None:
                # ENFORCED: overrides whatever reasoning_effort (if any) the
                # client requested. This is the only documented enforceable
                # xAI knob; it is a hint the provider may not obey exactly,
                # never a guaranteed numeric cap (see transport-notes.md).
                wire_payload["reasoning_effort"] = self.server.reasoning_effort
            if self.server.upstream_stream:
                # GEPA still sends and receives ordinary JSON. Only the
                # broker/provider leg streams, exposing timing and partial
                # reasoning evidence without changing native GEPA's API.
                if "max_tokens" in wire_payload:
                    wire_payload["max_completion_tokens"] = wire_payload.pop("max_tokens")
                wire_payload["stream"] = True
                wire_payload["stream_options"] = {"include_usage": True}
            changed = wire_payload != payload
            wire_body = json.dumps(wire_payload).encode() if changed else body
            if len(wire_body) > self.server.max_prompt_bytes:
                raise ValueError("forwarded request byte cap exceeded")
            attempt_id = self.server.ledger.reserve(
                len(wire_body), output_tokens + self.server.reasoning_reserve, role=role)
        except BudgetExceeded as exc:
            self._json(429, {"error": {"message": str(exc), "type": "budget_exhausted"}})
            return
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": {"message": str(exc)}})
            return
        key = os.environ.get(self.server.api_key_env)
        receipt = {"attempt_id": attempt_id, "role": role,
                   "request_at_utc": _utc_now(), "request_bytes": len(body),
                   "request_sha256": hashlib.sha256(body).hexdigest(),
                   "forwarded_request_bytes": len(wire_body),
                   "forwarded_request_sha256": hashlib.sha256(wire_body).hexdigest(),
                   "declared_context_sha256": context_hash,
                   "declared_archive_ids": archive_ids,
                   "upstream_endpoint": self.server.upstream_url + "/chat/completions",
                   "request_payload": _sanitize(payload, key),
                   "forwarded_request_payload": _sanitize(wire_payload, key),
                   "response_payload": None, "response_status": None,
                   "latency_seconds": None, "finish_reason": None,
                   "response_role": None}
        try:
            self.server.ledger.write_receipt(attempt_id, receipt)
        except OSError:
            self.server.ledger.settle(attempt_id, status="receipt_error")
            self._json(500, {"error": {"message": "audit receipt unavailable; broker stopped"}})
            return
        if not key:
            self.server.ledger.settle(attempt_id, status="missing_credential")
            receipt.update(response_status=503, latency_seconds=time.monotonic() - request_started,
                           error="missing_credential")
            self.server.ledger.write_receipt(attempt_id, receipt)
            self._json(503, {"error": {"message": "upstream credential unavailable"}})
            return
        request = urllib.request.Request(
            self.server.upstream_url + "/chat/completions", data=wire_body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
            method="POST")
        opener = urllib.request.build_opener(_NoRedirectHandler())
        settled = False
        raw = None
        stream_progress = None
        retry_log = []
        try:
            try_index = 0
            while True:
                try_index += 1
                try_started = time.monotonic()
                try:
                    if streaming:
                        stream_progress = {"headers_seconds": None, "first_event_seconds": None,
                                           "first_reasoning_seconds": None, "first_content_seconds": None,
                                           "done_seconds": None, "cancelled_seconds": None,
                                           "reasoning_cap_exceeded_seconds": None, "response_bytes": 0,
                                           "event_count": 0, "reasoning_chars": 0,
                                           "content_chars": 0, "events": []}
                        reasoning_char_cap = (
                            self.server.reasoning_cap_tokens * _CONSERVATIVE_CHARS_PER_REASONING_TOKEN
                            if self.server.reasoning_cap_tokens is not None else None)
                        jsonl_path = self.server.ledger.receipts_dir / f"attempt-{attempt_id:04d}.jsonl"
                        result = _buffer_chat_stream(
                            lambda: opener.open(request, timeout=self.server.timeout),
                            deadline_seconds=self.server.timeout,
                            max_bytes=self.server.max_response_bytes,
                            started=request_started, progress=stream_progress,
                            reasoning_char_cap=reasoning_char_cap, jsonl_path=jsonl_path)
                        raw = json.dumps(result).encode()
                    else:
                        with opener.open(request, timeout=self.server.timeout) as response:
                            raw = response.read(self.server.max_response_bytes + 1)
                            if len(raw) > self.server.max_response_bytes:
                                raise ValueError("upstream response byte cap exceeded")
                            result = json.loads(raw)
                            if not isinstance(result, dict):
                                raise ValueError("invalid upstream response")
                    retry_log.append({"try": try_index, "outcome": "ok",
                                      "elapsed_seconds": time.monotonic() - try_started})
                    break
                except urllib.error.HTTPError as exc:
                    retry_after = None
                    if exc.headers is not None:
                        retry_after = exc.headers.get("Retry-After")
                    transient = (exc.code in _TRANSIENT_HTTP_CODES or
                                (exc.code == 429 and retry_after is not None))
                    # Any bytes of a streamed answer already received makes
                    # a retry non-idempotent; never retry that case.
                    partial_stream = (streaming and stream_progress is not None and
                                      stream_progress.get("response_bytes", 0) > 0)
                    can_retry = (self.server.retry_transient and transient and
                                not partial_stream and try_index < _MAX_TRANSIENT_TRIES)
                    retry_log.append({"try": try_index, "outcome": exc.code,
                                      "retry_after": retry_after, "partial_stream": partial_stream,
                                      "elapsed_seconds": time.monotonic() - try_started,
                                      "will_retry": can_retry})
                    if not can_retry:
                        raise
                    delay = _TRANSIENT_BACKOFF_SECONDS[try_index - 1]
                    if retry_after is not None:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass
                    time.sleep(delay)
                    continue
            choices = result.get("choices")
            first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first.get("message"), dict) else {}
            receipt.update(response_at_utc=_utc_now(), response_status=200,
                           response_bytes=len(raw), response_payload=_sanitize(result, key),
                           latency_seconds=time.monotonic() - request_started,
                           finish_reason=first.get("finish_reason"),
                           response_role=message.get("role"), retry_attempts=retry_log)
            if stream_progress is not None:
                receipt["stream_progress"] = _sanitize(_stream_snapshot(stream_progress), key)
            self.server.ledger.write_receipt(attempt_id, receipt)
            attempt = self.server.ledger.settle(attempt_id, usage=result.get("usage"))
            settled = True
            receipt["settlement"] = {key: attempt.get(key) for key in
                                     ("status", "charged_usd", "input_tokens", "output_tokens",
                                      "reservation_overrun")}
            receipt["broker_status"] = (502 if attempt["status"] == "missing_usage" or
                                        attempt["reservation_overrun"] else 200)
            self.server.ledger.write_receipt(attempt_id, receipt)
            if attempt["status"] == "missing_usage" or attempt["reservation_overrun"]:
                self._json(502, {"error": {"message": "upstream usage unbounded; broker stopped"}})
                self.server.shutdown_requested = True
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as exc:
            if settled:
                # The provider response and usage are already in the private
                # receipt. A downstream disconnect must not erase that proof.
                return
            response_body = None
            if isinstance(exc, urllib.error.HTTPError):
                response_body = exc.read(self.server.max_response_bytes + 1)
                if len(response_body) > self.server.max_response_bytes:
                    response_body = {"error": "upstream error body exceeded byte cap"}
                else:
                    try:
                        response_body = json.loads(response_body)
                    except (ValueError, TypeError):
                        response_body = response_body.decode("utf-8", "replace")
            elif raw is not None:
                try:
                    response_body = json.loads(raw)
                except (ValueError, TypeError):
                    response_body = raw.decode("utf-8", "replace")
            receipt.update(response_at_utc=_utc_now(),
                           response_status=exc.code if isinstance(exc, urllib.error.HTTPError) else 502,
                           response_payload=_sanitize(response_body, key),
                           latency_seconds=time.monotonic() - request_started,
                           error_type=type(exc).__name__, retry_attempts=retry_log)
            if stream_progress is not None:
                receipt["stream_progress"] = _sanitize(_stream_snapshot(stream_progress), key)
            self.server.ledger.write_receipt(attempt_id, receipt)
            self.server.ledger.settle(attempt_id, status="upstream_error")
            # A single upstream failure (timeout cancel, connection error) is
            # charged at the reservation and retried; the ledger only halts
            # after _MAX_CONSECUTIVE_FAILURES in a row, or immediately for a
            # reservation overrun. Only stop serving once actually halted.
            if self.server.ledger.snapshot().get("halted_reason"):
                self.server.shutdown_requested = True
            code = exc.code if isinstance(exc, urllib.error.HTTPError) else 502
            self._json(code, {"error": {"message": "upstream request failed", "type": "upstream_error"}})


def _dry_run_payload(config):
    """Build the exact would-be forwarded chat payload without sending it."""
    payload = {"model": config["model"],
               "messages": [{"role": "system",
                             "content": "<research_context placeholder; not sent by dry-run>"},
                            {"role": "user",
                             "content": "<gepa_reflection prompt placeholder; not sent by dry-run>"}],
               "max_completion_tokens": config["max_tokens"]}
    if config.get("reasoning_effort") is not None:
        payload["reasoning_effort"] = config["reasoning_effort"]
    if config.get("upstream_stream", True):
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serve", choices=["serve"], nargs="?")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the exact payload a run would send, without sending it")
    parser.add_argument("--run", help="run name; with --dry-run, reads "
                        "autoresearch/<run>/broker-config.json")
    parser.add_argument("--upstream-url")
    parser.add_argument("--model")
    parser.add_argument("--api-key-env", default="XAI_API_KEY")
    parser.add_argument("--ledger")
    parser.add_argument("--max-requests", type=int)
    parser.add_argument("--max-usd", type=float)
    parser.add_argument("--input-usd-per-million", type=float)
    parser.add_argument("--output-usd-per-million", type=float)
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--reasoning-reserve", type=int, default=20_000)
    parser.add_argument("--reasoning-effort", choices=sorted(_REASONING_EFFORTS),
                        help="ENFORCED: overrides any client-requested value "
                        "(see transport-notes.md; not a guaranteed numeric cap)")
    parser.add_argument("--reasoning-cap-tokens", type=int,
                        help="abort an upstream-stream request once cumulative "
                        "reasoning characters cross a conservative estimate of "
                        "this many tokens; bounds actual charge at the reservation")
    parser.add_argument("--timeout", type=int, default=180,
                        help="upstream request timeout in seconds")
    parser.add_argument("--upstream-stream", action="store_true",
                        help="buffer upstream SSE into JSON for ordinary clients")
    parser.add_argument("--retry-transient", action=argparse.BooleanOptionalAction,
                        default=True,
                        help="retry a transient upstream 502/503/504 or "
                        "429-with-Retry-After up to 3 times within the same "
                        "reserved slot before settling (default: true)")
    parser.add_argument("--resume", action="store_true",
                        help="clear a halted ledger's halted_reason with a "
                        "permanent audit entry; requires --ledger and --note. "
                        "Never hand-edit the ledger file to do this.")
    parser.add_argument("--note", help="--resume: required audit note explaining why")
    parser.add_argument("--who", default="orchestrator",
                        help="--resume: audit entry attribution (default: orchestrator)")
    args = parser.parse_args()

    if args.resume:
        if not args.ledger:
            raise SystemExit("--resume requires --ledger <path>")
        if not args.note:
            raise SystemExit("--resume requires --note \"<why>\"")
        ledger_path = Path(args.ledger)
        existing = json.loads(ledger_path.read_text())
        limits = existing["limits"]
        ledger = DurableBudget(ledger_path, max_requests=limits["max_requests"],
                               max_usd=limits["max_usd"], input_rate=limits["input_rate"],
                               output_rate=limits["output_rate"])
        try:
            entry = ledger.resume(note=args.note, who=args.who)
        finally:
            ledger.close()
        print(json.dumps({"resumed": True, "ledger": args.ledger, "entry": entry}, indent=2))
        return

    if args.dry_run:
        if not args.run:
            raise SystemExit("--dry-run requires --run <name>")
        config_path = Path("autoresearch") / args.run / "broker-config.json"
        config = json.loads(config_path.read_text())
        print(json.dumps({
            "run": args.run,
            "upstream_endpoint": config["upstream_url"].rstrip("/") + "/chat/completions",
            "would_send_payload": _dry_run_payload(config),
            "reservation_usd_per_request_conservative": config["reservation_usd_per_request_conservative"],
            "max_requests": config["max_requests"], "max_usd": config["max_usd"],
        }, indent=2))
        return

    missing = [flag for flag, value in (
        ("--upstream-url", args.upstream_url), ("--model", args.model),
        ("--ledger", args.ledger), ("--max-requests", args.max_requests),
        ("--max-usd", args.max_usd), ("--input-usd-per-million", args.input_usd_per_million),
        ("--output-usd-per-million", args.output_usd_per_million)) if value is None]
    if args.serve != "serve" or missing:
        raise SystemExit("serve mode requires: serve " + " ".join(missing))

    ledger = DurableBudget(args.ledger, max_requests=args.max_requests,
                           max_usd=args.max_usd,
                           input_rate=args.input_usd_per_million,
                           output_rate=args.output_usd_per_million)
    broker = Broker(("127.0.0.1", args.port), upstream_url=args.upstream_url,
                    model=args.model, api_key_env=args.api_key_env, ledger=ledger,
                    max_tokens=args.max_tokens, reasoning_reserve=args.reasoning_reserve,
                    timeout=args.timeout, upstream_stream=args.upstream_stream,
                    reasoning_effort=args.reasoning_effort,
                    reasoning_cap_tokens=args.reasoning_cap_tokens,
                    retry_transient=args.retry_transient)
    print(json.dumps({"base_url": "http://127.0.0.1:%d/v1" % broker.server_port,
                      "model": args.model, "ledger": args.ledger}), flush=True)
    try:
        while not getattr(broker, "shutdown_requested", False):
            broker.handle_request()
    finally:
        broker.server_close()
        ledger.close()


if __name__ == "__main__":
    main()
