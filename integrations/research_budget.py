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
                              halted_reason=None)
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
            if status != "ok" or attempt["reservation_overrun"]:
                self.state["halted_reason"] = (
                    "reservation overrun" if attempt["reservation_overrun"] else status)
            self._save()
            return attempt.copy()

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))


class Broker(HTTPServer):
    def __init__(self, address, *, upstream_url, model, api_key_env, ledger,
                 max_prompt_bytes=120_000, max_response_bytes=8_000_000,
                 max_tokens=4000, reasoning_reserve=20_000, timeout=180):
        _validate_https_url(upstream_url)
        if not model or not api_key_env.isidentifier():
            raise ValueError("invalid model or credential variable")
        if any(type(x) is not int or x < 1 for x in
               (max_prompt_bytes, max_response_bytes, max_tokens, timeout)):
            raise ValueError("invalid positive limit")
        if type(reasoning_reserve) is not int or reasoning_reserve < 0:
            raise ValueError("invalid reasoning reserve")
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("broker may bind only to loopback")
        self.upstream_url = upstream_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.ledger = ledger
        self.max_prompt_bytes = max_prompt_bytes
        self.max_response_bytes = max_response_bytes
        self.max_tokens = max_tokens
        self.reasoning_reserve = reasoning_reserve
        self.timeout = timeout
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
                        "response_format", "stream", "n"}
            if set(payload) - accepted:
                raise ValueError("unsupported chat request fields")
            if payload.get("n", 1) != 1 or type(payload.get("n", 1)) is not int:
                raise ValueError("n must equal 1")
            if "max_tokens" in payload and "max_completion_tokens" in payload:
                raise ValueError("specify one output token bound")
            if payload.get("stream"):
                raise ValueError("streaming is unsupported by the budget broker")
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
            attempt_id = self.server.ledger.reserve(
                len(body), output_tokens + self.server.reasoning_reserve, role=role)
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
                   "declared_context_sha256": context_hash,
                   "declared_archive_ids": archive_ids,
                   "upstream_endpoint": self.server.upstream_url + "/chat/completions",
                   "request_payload": _sanitize(payload, key),
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
            self.server.upstream_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
            method="POST")
        opener = urllib.request.build_opener(_NoRedirectHandler())
        settled = False
        raw = None
        try:
            with opener.open(request, timeout=self.server.timeout) as response:
                raw = response.read(self.server.max_response_bytes + 1)
                if len(raw) > self.server.max_response_bytes:
                    raise ValueError("upstream response byte cap exceeded")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError("invalid upstream response")
            choices = result.get("choices")
            first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first.get("message"), dict) else {}
            receipt.update(response_at_utc=_utc_now(), response_status=200,
                           response_bytes=len(raw), response_payload=_sanitize(result, key),
                           latency_seconds=time.monotonic() - request_started,
                           finish_reason=first.get("finish_reason"),
                           response_role=message.get("role"))
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
                           error_type=type(exc).__name__)
            self.server.ledger.write_receipt(attempt_id, receipt)
            self.server.ledger.settle(attempt_id, status="upstream_error")
            code = exc.code if isinstance(exc, urllib.error.HTTPError) else 502
            self._json(code, {"error": {"message": "upstream request failed", "type": "upstream_error"}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serve", choices=["serve"])
    parser.add_argument("--upstream-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env", default="XAI_API_KEY")
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--max-requests", type=int, required=True)
    parser.add_argument("--max-usd", type=float, required=True)
    parser.add_argument("--input-usd-per-million", type=float, required=True)
    parser.add_argument("--output-usd-per-million", type=float, required=True)
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--reasoning-reserve", type=int, default=20_000)
    parser.add_argument("--timeout", type=int, default=180,
                        help="upstream request timeout in seconds")
    args = parser.parse_args()
    ledger = DurableBudget(args.ledger, max_requests=args.max_requests,
                           max_usd=args.max_usd,
                           input_rate=args.input_usd_per_million,
                           output_rate=args.output_usd_per_million)
    broker = Broker(("127.0.0.1", args.port), upstream_url=args.upstream_url,
                    model=args.model, api_key_env=args.api_key_env, ledger=ledger,
                    max_tokens=args.max_tokens, reasoning_reserve=args.reasoning_reserve,
                    timeout=args.timeout)
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
