"""One budgeted Grok-4.7 chat latency probe; never print the credential."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
OUT = ROOT / "chat-latency-probe-01"
PORT = 8877


def _credential() -> str:
    for line in (PROJECT / ".env").read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "XAI_API_KEY":
            return value.strip().strip('"').strip("'")
    raise RuntimeError("XAI_API_KEY missing")


def _deadline(_signum, _frame):
    raise TimeoutError("probe total wall deadline")


def main() -> int:
    if OUT.exists():
        raise FileExistsError(OUT)
    first = json.loads((ROOT / "broker-ledger.json").read_text())
    recovery = json.loads((ROOT / "broker-ledger-recovery-01.json").read_text())
    if (len(first["attempts"]), len(recovery["attempts"])) != (1, 1):
        raise RuntimeError("prior generation ledger changed")
    prior_spend = first["spent_usd"] + recovery["spent_usd"]
    remaining = round(5.0 - prior_spend, 7)
    if remaining <= 0:
        raise RuntimeError("shared campaign spend exhausted")
    OUT.mkdir(mode=0o700)
    os.chmod(OUT, 0o700)
    broker_log = (OUT / "broker.log").open("w")
    env = dict(os.environ)
    env["XAI_API_KEY"] = _credential()
    command = [sys.executable, "-m", "integrations.research_budget", "serve",
               "--upstream-url", "https://api.x.ai/v1", "--model", "grok-4.7",
               "--ledger", str(OUT / "ledger.json"), "--max-requests", "1",
               "--max-usd", str(remaining), "--input-usd-per-million", "2.2",
               "--output-usd-per-million", "6.6", "--port", str(PORT),
               "--max-tokens", "32", "--reasoning-reserve", "20000",
               "--timeout", "30"]
    process = subprocess.Popen(command, cwd=PROJECT, env=env, stdout=broker_log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    started = time.monotonic()
    result = {"kind": "readiness_probe", "model": "grok-4.7",
              "prior_generation_attempts": 2, "prior_generation_charged_usd": prior_spend,
              "prior_metadata_get_contacts": 1, "broker_max_requests": 1,
              "broker_max_usd": remaining, "broker_timeout_seconds": 30,
              "wall_deadline_seconds": 45, "max_completion_tokens": 32,
              "reasoning_effort": "low"}
    previous_handler = signal.signal(signal.SIGALRM, _deadline)
    signal.alarm(45)
    try:
        for _ in range(50):
            if process.poll() is not None:
                raise RuntimeError("budget broker stopped before probe")
            try:
                with urlopen(f"http://127.0.0.1:{PORT}/health", timeout=0.5):
                    break
            except (URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("budget broker did not become ready")
        payload = {"model": "grok-4.7", "messages": [
            {"role": "user", "content": "LRX API latency diagnostic. Reply exactly LRX_READY."}],
            "max_completion_tokens": 32, "reasoning_effort": "low"}
        request = Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                          json.dumps(payload).encode(),
                          {"Content-Type": "application/json",
                           "X-LRX-Call-Role": "gepa_preflight"})
        try:
            with urlopen(request, timeout=36) as response:
                answer = json.load(response)
                result["broker_http_status"] = response.status
                choice = answer.get("choices", [{}])[0]
                result["finish_reason"] = choice.get("finish_reason")
                result["reply_exact"] = choice.get("message", {}).get("content", "").strip() == "LRX_READY"
                result["usage_present"] = isinstance(answer.get("usage"), dict)
        except HTTPError as error:
            result["broker_http_status"] = error.code
            result["error_type"] = "HTTPError"
    except (TimeoutError, URLError, OSError, ValueError, RuntimeError) as error:
        result["error_type"] = type(error).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        broker_log.close()
        ledger = OUT / "ledger.json"
        if ledger.exists():
            state = json.loads(ledger.read_text())
            result["upstream_attempts"] = len(state["attempts"])
            result["ledger_spent_usd"] = state["spent_usd"]
            result["ledger_halted_reason"] = state["halted_reason"]
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True))
    return 0 if result.get("broker_http_status") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
