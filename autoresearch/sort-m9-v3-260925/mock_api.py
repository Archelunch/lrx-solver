"""Offline OpenAI-compatible responder for loop-v3 smokes (no provider calls).

Usage: python mock_api.py PORT LOG.jsonl CAPTURE_DIR [LEDGER.json]
Extends autoresearch/sort-m9-260925/mock_api.py: counts the SORT_PACKET_V2 marker,
answers diagnosis requests (system message REFLECT_SYSTEM) with prose plus a code
fence that the client must strip, and, given a ledger path, writes broker-style
receipts to LEDGER.json.receipts/attempt-NNNN.json so the post-run first-prompt
and EvoX leak checks read the same files they read in a live run. Proposals are
real sort_word programs: variant 2 is the cyclic-sweep seed, other variants the
naive control, selected by a harmless module constant MOCK_VARIANT; a SkyDiscover
variant 3 also gets an early empty return so the stage-1 screen rejection is exercised.
With MOCK_GEPA_BETTER=PATH in the environment, a GEPA reflection request whose prompt does not
yet contain that program gets it as the proposal (an accepted child; evaluated by the trusted
verifier under Seatbelt like any candidate).
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
NAIVE = (ROOT / "integrations" / "sort_control_naive.py").read_text()
SWEEP = (ROOT / "integrations" / "sort_control_sweep.py").read_text()
STRATEGY = (ROOT / ".venv-official" / "lib" / "python3.12" / "site-packages" / "skydiscover" / "optimize" /
            "search" / "evox" / "database" / "initial_search_strategy.py").read_text()
REFLECT = "Do not write code."
BETTER = Path(os.environ["MOCK_GEPA_BETTER"]).read_text() if os.environ.get("MOCK_GEPA_BETTER") else None
VARIANTS = [1, 2, 3]
PATTERN = re.compile(r"MOCK_VARIANT = (\d+)")
LOG = Path(sys.argv[2])
CAPTURE = Path(sys.argv[3])
RECEIPTS = Path(sys.argv[4] + ".receipts") if len(sys.argv) > 4 else None
LOCK = threading.Lock()


def with_knob(source, k):
    return source.replace("\n\ndef sort_word(v):", f"\n\nMOCK_VARIANT = {k}\n\n\ndef sort_word(v):", 1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/v1/models", "/health"):
            return self.reply(404, {"error": "not found"})
        return self.reply(200, {"object": "list", "data": [{"id": "mock", "object": "model"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        messages = body.get("messages", [])
        text = json.dumps(messages)
        role = self.headers.get("X-LRX-Call-Role", "")
        with LOCK:
            CAPTURE.mkdir(parents=True, exist_ok=True)
            index = len(list(CAPTURE.glob("request-*.json"))) + 1
            (CAPTURE / f"request-{index:04d}.json").write_text(json.dumps({"role": role, "body": body}))
            if RECEIPTS:
                RECEIPTS.mkdir(parents=True, exist_ok=True)
                (RECEIPTS / f"attempt-{index:04d}.json").write_text(json.dumps(
                    {"attempt_id": index, "role": role or "unknown", "request_payload": body, "finish_reason": "stop"}))
        plain = text.replace('\\"', '"').replace("\\'", "'")
        cut = plain.find("## Program Information")
        found = PATTERN.findall(plain[cut:] if cut >= 0 else plain)
        current = int(found[0]) if found else None
        nxt = VARIANTS[(VARIANTS.index(current) + 1) % len(VARIANTS)] if current in VARIANTS else 2
        if messages and REFLECT in messages[0].get("content", ""):
            kind = "diagnosis"
            content = ("The worst states are near-reversals at the top layers; the sweep leaves every shortest "
                       "path early. Choose the final rotation before sweeping.\n```python\nprint('stripped')\n```")
        elif "EvolvedProgramDatabase" in text and ("database" in text.lower() or "search algorithm" in text.lower()):
            kind, content = "strategy", "```python\n" + STRATEGY + "\n```"
        elif "variation operator" in text.lower() or "diverge" in text.lower():
            kind, content = "variation", "Try sweeping in both directions and choosing the final rotation."
        elif "sort_word" not in plain:
            kind, content = "probe", "OK"
        elif BETTER and role == "gepa_reflection" and BETTER.strip().splitlines()[0] not in plain:
            kind, content = "solution_better", "Here is the program.\n```python\n" + BETTER.rstrip() + "\n```\n"
        elif role in ("gepa_reflection", "sequential_refinement"):
            kind = "solution_full"
            content = "Here is the program.\n```python\n" + with_knob(SWEEP if nxt == 2 else NAIVE, nxt) + "```\n"
        elif current is None:
            kind = "solution_diff"
            content = ("<<<<<<< SEARCH\ndef sort_word(v):\n=======\nMOCK_VARIANT = %d\n\n\ndef sort_word(v):\n"
                       ">>>>>>> REPLACE" % nxt)
        else:
            kind = "solution_diff"
            content = f"<<<<<<< SEARCH\nMOCK_VARIANT = {current}\n=======\nMOCK_VARIANT = {nxt}\n>>>>>>> REPLACE"
            if nxt == 3 and "if MOCK_VARIANT == 3:" not in plain[cut:]:
                # variant 3 returns empty words (NOT_SORTED everywhere): exercises the stage-1 screen rejection
                content += ("\n<<<<<<< SEARCH\ndef sort_word(v):\n=======\ndef sort_word(v):\n"
                            "    if MOCK_VARIANT == 3:\n        return ''\n>>>>>>> REPLACE")
        with LOCK, LOG.open("a") as log:
            log.write(json.dumps({"t": time.time(), "kind": kind, "role": role, "model": body.get("model"),
                                  "packet_v2_count": text.count("SORT_PACKET_V2"),
                                  "diagnosis_attached": "Reviewer diagnosis (separate model" in text,
                                  "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "request_chars": len(text), "max_tokens": body.get("max_tokens"),
                                  "current_variant": current, "proposed_variant": nxt}) + "\n")
        return self.reply(200, {"id": f"mock-{time.time_ns()}", "object": "chat.completion",
                                "created": int(time.time()), "model": body.get("model", "mock"),
                                "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                             "finish_reason": "stop"}],
                                "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}})

    def reply(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
