"""Provider-neutral model adapter for LRX policy proposals.

OpenAI-compatible xAI HTTPS adapter via stdlib urllib.
- allow_network=False by default; must be set True explicitly.
- API key read from XAI_API_KEY env var at call time; never stored in repr/str.
- Redirects disallowed to prevent auth-token leakage.
- Response bytes capped; max_requests enforced.
- BudgetLedger: reserve before network call, charge reservation on failure.
  Missing or invalid usage does not release the reservation.
- Cost estimates are based on user-supplied rates. This is not a hard billing
  guarantee from the provider.
- propose() parses JSON from assistant text with json.loads; no exec/eval.
- Endpoint must be HTTPS with no embedded credentials or query parameters.
- Live API never called in this file's test suite.
"""

import json
import os
import math
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# ProposalBudget (simple tracking, kept for API compatibility)
# ---------------------------------------------------------------------------


@dataclass
class ProposalBudget:
    """Simple request/token budget without pre-reservation."""

    max_total_cost: Optional[float] = None
    input_cost_per_mtok: float = 0.0
    output_cost_per_mtok: float = 0.0
    requests_made: int = 0
    tokens_input: int = 0
    tokens_output: int = 0

    def update(self, input_tokens: int, output_tokens: int) -> None:
        """Track actual usage."""
        self.tokens_input += input_tokens
        self.tokens_output += output_tokens
        self.requests_made += 1

    def estimated_cost(self) -> float:
        """Estimate cost from recorded usage and user-supplied rates."""
        return (self.tokens_input / 1_000_000) * self.input_cost_per_mtok + (
            self.tokens_output / 1_000_000
        ) * self.output_cost_per_mtok

    def can_afford_request(self, est_tokens: int = 1000) -> bool:
        """Return True if budget headroom allows another request."""
        if self.max_total_cost is None:
            return False  # offline-only mode
        current = self.estimated_cost()
        est_add = (est_tokens / 1_000_000) * (
            self.input_cost_per_mtok + self.output_cost_per_mtok
        )
        return current + est_add <= self.max_total_cost


# ---------------------------------------------------------------------------
# BudgetLedger (reservation-based, used by XAIAdapter)
# ---------------------------------------------------------------------------


class BudgetLedger:
    """Tracks API spend with pre-reservation semantics.

    Workflow:
        reserve() -> network call -> commit()   [success]
        reserve() -> network call failure -> charge_reservation()  [failure]

    Failed calls are charged the reservation amount. There is no auto-retry.
    Invalid usage (missing fields, negative counts) raises without releasing
    the reservation; caller must call charge_reservation() explicitly.
    Cost estimates use caller-supplied rates and are NOT a billing guarantee.
    """

    def __init__(
        self,
        max_spend: float,
        input_cost_per_mtok: float,
        output_cost_per_mtok: float,
    ) -> None:
        if (
            type(max_spend) not in (int, float)
            or not math.isfinite(max_spend)
            or max_spend <= 0
        ):
            raise ValueError("max_spend must be a positive number")
        if (
            type(input_cost_per_mtok) not in (int, float)
            or not math.isfinite(input_cost_per_mtok)
            or input_cost_per_mtok <= 0
        ):
            raise ValueError("input_cost_per_mtok must be a positive number")
        if (
            type(output_cost_per_mtok) not in (int, float)
            or not math.isfinite(output_cost_per_mtok)
            or output_cost_per_mtok <= 0
        ):
            raise ValueError("output_cost_per_mtok must be a positive number")
        self.max_spend = float(max_spend)
        self._in_rate = float(input_cost_per_mtok)
        self._out_rate = float(output_cost_per_mtok)
        self._committed: float = 0.0
        self._reserved: float = 0.0
        self.requests_made: int = 0
        self.tokens_input = self.tokens_output = 0
        self.failed_requests = 0

    def _cost(self, in_tok: int, out_tok: int) -> float:
        return (in_tok / 1_000_000) * self._in_rate + (
            out_tok / 1_000_000
        ) * self._out_rate

    def estimated_cost(self) -> float:
        """Committed spend (excludes current reservation)."""
        return self._committed

    def reserve(self, max_prompt_tokens: int, max_output_tokens: int) -> bool:
        """Pre-reserve conservative estimated cost for one request.

        Returns True if budget allows; False if headroom is insufficient.
        Only one pending reservation is tracked at a time.
        """
        if self._reserved:
            raise RuntimeError("A request reservation is already pending")
        if any(
            type(v) is not int or v <= 0 for v in (max_prompt_tokens, max_output_tokens)
        ):
            raise ValueError("Reservation token bounds must be positive integers")
        est = self._cost(max_prompt_tokens, max_output_tokens)
        if self._committed + self._reserved + est > self.max_spend:
            return False
        self._reserved = est
        return True

    def commit(self, actual_input_tokens: int, actual_output_tokens: int) -> None:
        """Finalise charge with actual usage. Clears reservation.

        Raises:
            ValueError: if token counts are not non-negative integers.
        """
        if type(actual_input_tokens) is not int or actual_input_tokens < 0:
            raise ValueError(
                f"actual_input_tokens must be a non-negative int, "
                f"got {actual_input_tokens!r}"
            )
        if type(actual_output_tokens) is not int or actual_output_tokens < 0:
            raise ValueError(
                f"actual_output_tokens must be a non-negative int, "
                f"got {actual_output_tokens!r}"
            )
        self._committed += self._cost(actual_input_tokens, actual_output_tokens)
        self.tokens_input += actual_input_tokens
        self.tokens_output += actual_output_tokens
        self._reserved = 0.0
        self.requests_made += 1

    def charge_reservation(self) -> None:
        """Charge the pending reservation (no refund). Call on failure."""
        self._committed += self._reserved
        self._reserved = 0.0
        self.requests_made += 1
        self.failed_requests += 1


# ---------------------------------------------------------------------------
# OfflineMockProposer
# ---------------------------------------------------------------------------


class OfflineMockProposer:
    """Deterministic offline word proposals for testing without network."""

    def __init__(self, m: int, r: int, seed: int = 42):
        self.m = m
        self.r = r
        self.seed = seed

    def propose_words(
        self, count: int = 5, problem_description: Optional[str] = None
    ) -> List[str]:
        """Generate mock word proposals (L/R/X only)."""
        import random

        rng = random.Random(self.seed)
        words = []
        for _ in range(count):
            length = rng.randint(20, 50)
            word = "".join(
                rng.choices(["L", "R", "X"], weights=[0.35, 0.35, 0.30], k=length)
            )
            words.append(word)
        return words


# ---------------------------------------------------------------------------
# URL validation helper
# ---------------------------------------------------------------------------


def _validate_https_url(url: str) -> None:
    """Raise ValueError unless url is HTTPS with no credentials or query."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"base_url must use HTTPS scheme, got scheme={parsed.scheme!r}"
        )
    if parsed.username or parsed.password:
        raise ValueError("base_url must not embed credentials")
    if parsed.query or parsed.fragment or not parsed.hostname:
        raise ValueError("base_url must have a host and no query or fragment")


# ---------------------------------------------------------------------------
# No-redirect handler
# ---------------------------------------------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject all HTTP redirects to prevent auth-token leakage."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError(
            f"Redirect to {newurl!r} rejected (redirects disallowed)"
        )

    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.URLError("Redirect 301 rejected")

    def http_error_302(self, req, fp, code, msg, headers):
        raise urllib.error.URLError("Redirect 302 rejected")

    def http_error_303(self, req, fp, code, msg, headers):
        raise urllib.error.URLError("Redirect 303 rejected")

    def http_error_307(self, req, fp, code, msg, headers):
        raise urllib.error.URLError("Redirect 307 rejected")


# ---------------------------------------------------------------------------
# Policy text extractor (no eval)
# ---------------------------------------------------------------------------


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Extract the first complete JSON object from text. No exec/eval."""
    if not isinstance(text, str):
        raise ValueError("Model content must be text")
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in model response") from None
    return value


def _build_prompt(m: int, r: int, hint: Optional[str] = None) -> str:
    budget = m * (m + 1) // 2 + (r - 1) * (m - 2)
    base = (
        f"You are helping search for a beam-search policy for the LRX "
        f"marked-zero sorting problem with m={m}, r={r}, n={m + r}. "
        f"The conjectured budget bound is T={budget}. "
        f"Reply with ONLY a JSON object with keys: "
        f'"weights" (list of 3 positive integers for L/R/X priority), '
        f'"beam_width" (integer 1-50), "max_steps" (integer 1-5000). '
        f'Example: {{"weights": [4, 3, 2], "beam_width": 15, "max_steps": 400}}'
    )
    if hint:
        base += f" Context: {hint}"
    return base


# ---------------------------------------------------------------------------
# XAIAdapter
# ---------------------------------------------------------------------------


class XAIAdapter:
    """OpenAI-compatible HTTPS adapter for xAI (or any compatible endpoint).

    API key is read from XAI_API_KEY at call time; never stored as an
    instance attribute so it does not appear in repr(), str(), or logs.

    Cost estimates use user-supplied rates. This is not a hard billing
    guarantee from the provider.

    allow_network=False (default): any call to propose() raises immediately.
    """

    def __init__(
        self,
        base_url: str = "https://api.x.ai/v1",
        model: str = "grok-4.7",
        allow_network: bool = False,
        timeout_sec: int = 30,
        max_requests: int = 10,
        max_output_tokens: int = 200,
        max_prompt_bytes: int = 8_192,
        max_response_bytes: int = 65_536,
        api_key_env: str = "XAI_API_KEY",
    ) -> None:
        _validate_https_url(base_url)
        if type(allow_network) is not bool:
            raise ValueError("allow_network must be an explicit boolean")
        for value, limit in [
            (timeout_sec, 120),
            (max_requests, 1000),
            (max_output_tokens, 8192),
            (max_prompt_bytes, 65536),
            (max_response_bytes, 1_000_000),
        ]:
            if type(value) is not int or not 1 <= value <= limit:
                raise ValueError("Invalid adapter resource limit")
        if not isinstance(model, str) or not model or len(model) > 200:
            raise ValueError("Invalid model ID")
        if not isinstance(api_key_env, str) or not api_key_env.isidentifier():
            raise ValueError("Invalid API key environment variable name")
        self._base_url = base_url
        self._model = model
        self._allow_network = allow_network
        self._timeout_sec = int(timeout_sec)
        self._max_requests = int(max_requests)
        self._max_output_tokens = int(max_output_tokens)
        self._max_prompt_bytes = int(max_prompt_bytes)
        self._max_response_bytes = int(max_response_bytes)
        self._ledger: Optional[BudgetLedger] = None
        self._api_key_env = api_key_env
        self._attempts = 0
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        # Intentionally omits API key.
        return (
            f"XAIAdapter(base_url={self._base_url!r}, "
            f"model={self._model!r}, "
            f"allow_network={self._allow_network})"
        )

    def __str__(self) -> str:
        return repr(self)

    def attach_ledger(self, ledger: BudgetLedger) -> None:
        """Attach a BudgetLedger to track spend."""
        if not isinstance(ledger, BudgetLedger):
            raise TypeError("ledger must be a BudgetLedger instance")
        if self._attempts or self._ledger is not None:
            raise RuntimeError("Cannot replace an attached campaign budget")
        self._ledger = ledger

    def propose(
        self,
        m: int,
        r: int,
        policy_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request a beam-search policy JSON from the model.

        Returns:
            Parsed policy dict with keys weights, beam_width, max_steps.

        Raises:
            RuntimeError: if allow_network=False, or budget/request limits hit.
            ValueError: on invalid API response or usage fields.
        """
        with self._lock:
            return self._propose(m, r, policy_hint)

    def _propose(self, m, r, policy_hint):
        if not self._allow_network:
            raise RuntimeError(
                "Network disabled (allow_network=False). "
                "Set allow_network=True to make live calls."
            )
        if self._ledger is None:
            raise RuntimeError("No BudgetLedger attached. Call attach_ledger() first.")
        if self._attempts >= self._max_requests:
            raise RuntimeError(
                f"Request limit {self._max_requests} reached; no further calls."
            )

        prompt = _build_prompt(m, r, policy_hint)
        prompt_bytes = prompt.encode("utf-8")
        if len(prompt_bytes) > self._max_prompt_bytes:
            raise ValueError("Prompt exceeds byte cap")

        # Byte-level estimate plus message overhead; not a provider billing guarantee.
        conservative_prompt_tokens = len(prompt_bytes) + 256
        if not self._ledger.reserve(
            conservative_prompt_tokens, self._max_output_tokens
        ):
            raise RuntimeError(
                "Budget exhausted; cannot reserve for another request. "
                "This is an estimate based on user-supplied rates, not a "
                "hard provider billing guarantee."
            )

        self._attempts += 1
        try:
            content, usage_raw = self._http_post(prompt)
        except Exception:
            self._ledger.charge_reservation()
            raise

        # Validate usage — do NOT release reservation on invalid fields.
        if not isinstance(usage_raw, dict):
            self._ledger.charge_reservation()
            raise ValueError("Response usage field missing or invalid")
        in_tok = usage_raw.get("prompt_tokens")
        out_tok = usage_raw.get("completion_tokens")
        if type(in_tok) is not int or in_tok < 0:
            self._ledger.charge_reservation()
            raise ValueError("Invalid prompt_tokens in usage")
        if type(out_tok) is not int or out_tok < 0:
            self._ledger.charge_reservation()
            raise ValueError("Invalid completion_tokens in usage")

        self._ledger.commit(in_tok, out_tok)
        if in_tok > conservative_prompt_tokens or out_tok > self._max_output_tokens:
            self._max_requests = self._attempts
            raise ValueError(
                "Provider usage exceeded reservation assumptions; campaign stopped"
            )
        from .candidate_runner import parse_policy

        return parse_policy(_extract_json_object(content))

    def propose_policy(self, m, r, parent=None, feedback=None, seed=0):
        context = json.dumps(
            {"parent": parent, "feedback": feedback, "proposal_seed": seed}
        )
        return self.propose(m, r, policy_hint=context)

    def usage(self):
        return {
            "model": self._model,
            "base_url": self._base_url,
            "requests": self._attempts,
            "estimated_usd": self._ledger.estimated_cost() if self._ledger else 0,
            "input_tokens": self._ledger.tokens_input if self._ledger else 0,
            "output_tokens": self._ledger.tokens_output if self._ledger else 0,
            "unknown_usage_requests": self._ledger.failed_requests
            if self._ledger
            else 0,
            "billing_verified": False,
        }

    def configuration(self):
        return {
            "model": self._model,
            "base_url": self._base_url,
            "max_requests": self._max_requests,
            "max_output_tokens": self._max_output_tokens,
            "timeout_seconds": self._timeout_sec,
            "max_spend": self._ledger.max_spend if self._ledger else None,
            "input_usd_per_million": self._ledger._in_rate if self._ledger else None,
            "output_usd_per_million": self._ledger._out_rate if self._ledger else None,
        }

    def _http_post(self, prompt: str) -> Tuple[str, Any]:
        """Make one HTTPS POST. Returns (content_str, usage_dict_or_None).

        Raises urllib.error.HTTPError / URLError on network errors.
        No redirects; response capped at max_response_bytes.
        API key read from environment at call time.
        """
        api_key = os.environ.get(self._api_key_env, "")
        if not api_key:
            raise ValueError("API key environment variable is not set")

        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self._max_output_tokens,
            }
        ).encode("utf-8")

        endpoint = self._base_url.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                # Auth header value constructed inline; not stored anywhere.
                "Authorization": "Bearer " + api_key,
            },
            method="POST",
        )

        opener = urllib.request.build_opener(_NoRedirectHandler())
        try:
            with opener.open(req, timeout=self._timeout_sec) as resp:
                raw = resp.read(self._max_response_bytes + 1)
                if len(raw) > self._max_response_bytes:
                    raise ValueError("API response exceeds byte cap")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Provider HTTP error {exc.code}") from None
        except (urllib.error.URLError, OSError):
            raise RuntimeError("Provider network request failed") from None

        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ValueError("Provider returned invalid JSON") from None
        if not isinstance(data, dict):
            raise ValueError("Provider returned a non-object response")
        usage = data.get("usage")
        choices = data.get("choices", [])
        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(choices[0], dict)
        ):
            raise ValueError("No choices in API response")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("Missing assistant text")
        content = message["content"]
        return content, usage
