"""Thread-safe OpenAI-compatible chat client with a spend ledger.

Used by v2 campaigns. The older `provider_adapter.XAIAdapter` stays for the
legacy policy experiment. Network is off unless allow_network=True. The API key
is read from the environment at call time and never stored or logged.

Costs are estimates from user-supplied USD-per-million-token rates. They are not
provider billing guarantees; set a provider-side limit as well.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .provider_adapter import _NoRedirectHandler, _validate_https_url


def load_dotenv(path=".env", keys=None):
    """Set missing environment variables from a KEY=VALUE file.

    Returns the names that were set (never the values). Existing environment
    variables win. Lines starting with # and blank lines are ignored.
    """
    path = Path(path)
    if not path.exists():
        return []
    loaded = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        value = value.strip().strip('"').strip("'")
        if not key.isidentifier() or (keys and key not in keys):
            continue
        if key not in os.environ and value:
            os.environ[key] = value
            loaded.append(key)
    return loaded


class SpendLedger:
    """Concurrent reservations: reserve -> call -> settle(actual) or settle(None)."""

    def __init__(
        self, max_spend_usd, input_usd_per_mtok, output_usd_per_mtok, max_requests
    ):
        for value in (max_spend_usd, input_usd_per_mtok, output_usd_per_mtok):
            if type(value) not in (int, float) or not value > 0:
                raise ValueError("spend limit and prices must be positive numbers")
        if type(max_requests) is not int or max_requests < 1:
            raise ValueError("max_requests must be a positive integer")
        self.max_spend = float(max_spend_usd)
        self.in_rate = float(input_usd_per_mtok)
        self.out_rate = float(output_usd_per_mtok)
        self.max_requests = max_requests
        self.committed = 0.0
        self.reserved = 0.0
        self.requests = 0
        self.failed = 0
        self.overruns = 0
        self.provider_costed = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self._lock = threading.Lock()

    def cost(self, tokens_in, tokens_out):
        return tokens_in / 1e6 * self.in_rate + tokens_out / 1e6 * self.out_rate

    def reserve(self, tokens_in, tokens_out):
        est = self.cost(tokens_in, tokens_out)
        with self._lock:
            if self.requests >= self.max_requests:
                raise BudgetExhausted(f"request limit {self.max_requests} reached")
            if self.committed + self.reserved + est > self.max_spend:
                raise BudgetExhausted(
                    f"spend limit ${self.max_spend:.2f} would be exceeded "
                    f"(committed ${self.committed:.4f})"
                )
            self.reserved += est
            self.requests += 1
        return est

    def settle(self, reservation, tokens_in=None, tokens_out=None, provider_cost=None):
        """Commit actual usage, or the whole reservation when usage is unknown.

        provider_cost (USD reported by the provider) wins over the rate estimate.
        """
        with self._lock:
            self.reserved -= reservation
            if tokens_in is None:
                self.committed += reservation
                self.failed += 1
                return reservation
            actual = self.cost(tokens_in, tokens_out)
            if provider_cost is not None:
                actual = provider_cost
                self.provider_costed += 1
            if actual > reservation:
                self.overruns += 1
            self.committed += actual
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out
            return actual

    def snapshot(self):
        with self._lock:
            return {
                "estimated_usd": round(self.committed, 6),
                "max_spend_usd": self.max_spend,
                "requests": self.requests,
                "failed_requests": self.failed,
                "usage_overruns": self.overruns,
                "provider_costed_requests": self.provider_costed,
                "input_tokens": self.tokens_in,
                "output_tokens": self.tokens_out,
                "billing_verified": False,
            }


class BudgetExhausted(RuntimeError):
    pass


class RequestAborted(RuntimeError):
    """We stopped a request ourselves (wall-clock or reasoning budget).

    `partial_reasoning` keeps what the model had streamed, for traces.
    """

    def __init__(self, message, partial_reasoning=""):
        super().__init__(message)
        self.partial_reasoning = partial_reasoning


class ChatClient:
    """OpenAI-compatible chat client with streaming and reasoning control.

    Reasoning models (grok-4.7) think before answering and neither max_tokens
    nor max_completion_tokens bounds that thinking (measured 2026-09-22). With
    stream=True the provider sends reasoning chunks as they are produced, so we
    can (a) avoid a single long silent read, (b) abort when the estimated
    reasoning exceeds max_reasoning_tokens or the wall clock exceeds
    timeout_sec, and (c) keep the reasoning text for traces. An aborted request
    is charged its whole reservation, since its real usage is unknown.
    """

    def __init__(
        self,
        base_url,
        model,
        ledger,
        allow_network=False,
        api_key_env="XAI_API_KEY",
        max_output_tokens=4000,
        timeout_sec=600,
        idle_timeout_sec=120,
        max_reasoning_tokens=20_000,
        max_prompt_bytes=120_000,
        max_response_bytes=8_000_000,
        temperature=None,
        reasoning_effort=None,
        stream=True,
    ):
        _validate_https_url(base_url)
        if type(allow_network) is not bool:
            raise ValueError("allow_network must be an explicit boolean")
        if not isinstance(ledger, SpendLedger):
            raise TypeError("ledger must be a SpendLedger")
        if not isinstance(model, str) or not model or len(model) > 200:
            raise ValueError("invalid model id")
        if not isinstance(api_key_env, str) or not api_key_env.isidentifier():
            raise ValueError("invalid api_key_env")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 64_000:
            raise ValueError("max_output_tokens must be 1..64000")
        if (
            type(max_reasoning_tokens) is not int
            or not 0 <= max_reasoning_tokens <= 500_000
        ):
            raise ValueError("max_reasoning_tokens must be 0..500000")
        self.base_url = base_url
        self.model = model
        self.ledger = ledger
        self.allow_network = allow_network
        self.api_key_env = api_key_env
        self.max_output_tokens = max_output_tokens
        self.timeout_sec = timeout_sec
        self.idle_timeout_sec = idle_timeout_sec
        self.max_reasoning_tokens = max_reasoning_tokens
        self.max_prompt_bytes = max_prompt_bytes
        self.max_response_bytes = max_response_bytes
        self.temperature = temperature
        self.reasoning_effort = reasoning_effort
        self.stream = stream

    def __repr__(self):
        return f"ChatClient(base_url={self.base_url!r}, model={self.model!r})"

    def complete(self, messages):
        """Return dict(text, reasoning, tokens_in, tokens_out, reasoning_tokens,
        cost_usd, cost_source, seconds, finish_reason)."""
        if not self.allow_network:
            raise RuntimeError("network disabled; pass --allow-network to opt in")
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_output_tokens,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        body = json.dumps(payload).encode()
        if len(body) > self.max_prompt_bytes:
            raise ValueError("prompt exceeds byte cap")
        # Bytes bound prompt tokens; output reservation covers the answer plus
        # the reasoning allowance (reasoning is billed as output).
        reservation = self.ledger.reserve(
            len(body) + 512, self.max_output_tokens + self.max_reasoning_tokens
        )
        start = time.perf_counter()
        try:
            data = self._post(body, start)
            usage = data["usage"] or {}
            tokens_in = usage.get("prompt_tokens")
            tokens_out = usage.get("completion_tokens")
            if type(tokens_in) is not int or type(tokens_out) is not int:
                raise ValueError("response usage missing")
            details = usage.get("completion_tokens_details") or {}
            reasoning_tokens = details.get("reasoning_tokens") or 0
            if type(reasoning_tokens) is not int or reasoning_tokens < 0:
                raise ValueError("invalid reasoning_tokens")
            # xAI reports total = prompt + completion + reasoning, i.e. reasoning
            # is billed on top of completion_tokens.
            tokens_out += reasoning_tokens
            ticks = usage.get("cost_in_usd_ticks")
            provider_cost = ticks / 1e10 if type(ticks) is int and ticks >= 0 else None
        except Exception:
            self.ledger.settle(reservation)
            raise
        cost = self.ledger.settle(reservation, tokens_in, tokens_out, provider_cost)
        return {
            "text": data["text"],
            "reasoning": data["reasoning"],
            "finish_reason": data["finish_reason"],
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "reasoning_tokens": reasoning_tokens,
            "cost_usd": round(cost, 6),
            "cost_source": "provider" if provider_cost is not None else "rates",
            "seconds": round(time.perf_counter() - start, 2),
        }

    def _post(self, body, start):
        api_key = os.environ.get(self.api_key_env, "")
        if not api_key:
            raise ValueError(f"{self.api_key_env} is not set")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key,
            },
            method="POST",
        )
        opener = urllib.request.build_opener(_NoRedirectHandler())
        timeout = self.idle_timeout_sec if self.stream else self.timeout_sec
        try:
            with opener.open(request, timeout=timeout) as response:
                if self.stream:
                    return self._read_stream(response, start)
                raw = response.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(300).decode("utf-8", "replace")
            except Exception:
                pass
            raise RuntimeError(f"provider HTTP error {exc.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RuntimeError(
                f"provider network request failed ({type(exc).__name__}: {reason})"
            ) from None
        if len(raw) > self.max_response_bytes:
            raise ValueError("response exceeds byte cap")
        try:
            data = json.loads(raw)
        except ValueError:
            raise ValueError("provider returned invalid JSON") from None
        if not isinstance(data, dict) or not data.get("choices"):
            raise ValueError("no choices in provider response")
        choice = data["choices"][0]
        message = choice.get("message") or {}
        if not isinstance(message.get("content"), str):
            raise ValueError("missing assistant text")
        return {
            "text": message["content"],
            "reasoning": message.get("reasoning_content") or "",
            "finish_reason": choice.get("finish_reason"),
            "usage": data.get("usage"),
        }

    def _read_stream(self, response, start):
        """Parse server-sent events; enforce wall-clock and reasoning budgets."""
        text, reasoning = [], []
        reasoning_chars = 0
        usage, finish, total = None, None, 0
        # ~3 characters per token is a conservative (high) token estimate.
        reasoning_char_cap = self.max_reasoning_tokens * 3
        for raw in response:
            total += len(raw)
            if total > self.max_response_bytes:
                raise ValueError("response exceeds byte cap")
            if time.perf_counter() - start > self.timeout_sec:
                raise RequestAborted(
                    f"wall-clock cap {self.timeout_sec}s exceeded",
                    "".join(reasoning),
                )
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                event = json.loads(chunk)
            except ValueError:
                raise ValueError("provider sent invalid stream JSON") from None
            if event.get("usage"):
                usage = event["usage"]
            for choice in event.get("choices") or []:
                delta = choice.get("delta") or {}
                if isinstance(delta.get("content"), str):
                    text.append(delta["content"])
                if isinstance(delta.get("reasoning_content"), str):
                    reasoning.append(delta["reasoning_content"])
                    reasoning_chars += len(delta["reasoning_content"])
                    if reasoning_chars > reasoning_char_cap:
                        raise RequestAborted(
                            f"reasoning budget {self.max_reasoning_tokens} tokens exceeded",
                            "".join(reasoning),
                        )
                if choice.get("finish_reason"):
                    finish = choice["finish_reason"]
        if usage is None:
            raise ValueError("response usage missing")
        return {
            "text": "".join(text),
            "reasoning": "".join(reasoning),
            "finish_reason": finish,
            "usage": usage,
        }


def client_from_config(cfg, allow_network):
    """Build a ChatClient from a campaign provider config dict."""
    ledger = SpendLedger(
        cfg["max_spend_usd"],
        cfg["input_usd_per_mtok"],
        cfg["output_usd_per_mtok"],
        cfg.get("max_requests", 100),
    )
    return ChatClient(
        cfg.get("base_url", "https://api.x.ai/v1"),
        cfg["model"],
        ledger,
        allow_network=allow_network,
        api_key_env=cfg.get("api_key_env", "XAI_API_KEY"),
        max_output_tokens=cfg.get("max_output_tokens", 4000),
        timeout_sec=cfg.get("timeout_sec", 600),
        idle_timeout_sec=cfg.get("idle_timeout_sec", 120),
        max_reasoning_tokens=cfg.get("max_reasoning_tokens", 20_000),
        temperature=cfg.get("temperature"),
        reasoning_effort=cfg.get("reasoning_effort"),
        stream=cfg.get("stream", True),
    )
