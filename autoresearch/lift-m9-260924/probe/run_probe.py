#!/usr/bin/env python3
"""One live probe call per candidate model through the budget broker.

Usage: run_probe.py <config.json> <port>
Loads the captured GEPA first prompt, starts the broker with the config's
model/upstream/prices (own small probe ledger, never the campaign ledger),
sends one request, saves the response and extracted program, and evaluates
the program on the frozen development set. Keys come from the environment.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIFT = ROOT / "autoresearch" / "lift-m9-260924"
PROBE = LIFT / "probe"


def main():
    cfg_path, port = Path(sys.argv[1]), int(sys.argv[2])
    cfg = json.load(open(cfg_path))
    model = cfg["model"]
    tag = re.sub(r"[^a-z0-9.]+", "-", model.lower())
    ledger = PROBE / f"broker-ledger-probe-{tag}.json"
    assert not ledger.exists(), ledger
    body = json.load(open(LIFT / "first-prompt-capture" / "request-0001.json"))["body"]
    body["model"] = model
    body["max_tokens"] = cfg["max_tokens"]
    cmd = [sys.executable, "-m", "integrations.research_budget", "serve",
           "--upstream-url", cfg["upstream_url"], "--model", model,
           "--api-key-env", cfg["api_key_env"], "--ledger", str(ledger),
           "--max-requests", "2", "--max-usd", "2.0",
           "--input-usd-per-million", str(cfg["input_usd_per_million"]),
           "--output-usd-per-million", str(cfg["output_usd_per_million"]),
           "--port", str(port), "--max-tokens", str(cfg["max_tokens"]),
           "--reasoning-effort", cfg["reasoning_effort"],
           "--reasoning-cap-tokens", str(cfg["reasoning_cap_tokens"]),
           "--timeout", str(cfg["timeout"]), "--upstream-stream"]
    log = open(PROBE / f"broker-{tag}.log", "w")
    broker = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        time.sleep(2)
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer local",
                     "X-LRX-Call-Role": "gepa_reflection"})
        t0 = time.monotonic()
        status, text = None, None
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout"] + 60) as r:
                status, text = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode(errors="replace")
        elapsed = time.monotonic() - t0
        (PROBE / f"{tag}-response.json").write_text(text)
        result = dict(model=model, status=status, seconds=round(elapsed, 3))
        content = None
        try:
            resp = json.loads(text)
            content = resp["choices"][0]["message"]["content"]
            result["usage"] = resp.get("usage")
            result["finish_reason"] = resp["choices"][0].get("finish_reason")
        except Exception as exc:  # noqa: BLE001
            result["parse_error"] = repr(exc)[:300]
        if content:
            blocks = re.findall(r"```(?:python)?\n(.*?)```", content, re.S)
            src = max(blocks, key=len) if blocks else None
            result["code_blocks"] = len(blocks)
            if src:
                prog = PROBE / f"{tag}.py"
                prog.write_text(src)
                out = PROBE / f"{tag}-eval.json"
                ev = subprocess.run([sys.executable, "-m", "integrations.lift_evaluator",
                                     "--program", str(prog),
                                     "--instances", str(LIFT / "frozen" / "development.json"),
                                     "--output", str(out)], cwd=ROOT, capture_output=True, text=True)
                result["eval_returncode"] = ev.returncode
                if out.exists():
                    e = json.load(open(out))
                    result["eval"] = {k: e[k] for k in ("certificates", "valid", "timeouts", "seconds") if k in e}
                else:
                    result["eval_stderr"] = ev.stderr[-1500:]
        (PROBE / f"{tag}-result.json").write_text(json.dumps(result, indent=1))
        print(json.dumps(result))
    finally:
        broker.terminate()
        broker.wait(timeout=30)
        log.close()


if __name__ == "__main__":
    main()
