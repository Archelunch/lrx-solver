"""Offline OpenAI-compatible responder for bound-m engine smokes (no provider calls).

Usage: python mock_api.py PORT LOG.jsonl [CAPTURE_DIR]
Modeled on autoresearch/sort-m9-260925/mock_api.py. Every proposal is a real,
correct certify program built from trusted repository controls. The knob is a
harmless module constant MOCK_VARIANT. GEPA and the sequential control get full
fenced source: variant 2 is the b16 seed with KEEP = 32 (more words for the
evaluator's LP, so an accepted improvement is exercised); other variants are
the naive control. SkyDiscover gets a SEARCH/REPLACE diff on the knob. EvoX
strategy requests (never expected: strategy evolution is disabled) get the
upstream initial strategy. Every request is logged with whether the packet was
present.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
NAIVE = (ROOT / "integrations" / "bound_control_naive.py").read_text()
SWEEP = (ROOT / "integrations" / "bound_control_sweep.py").read_text().replace("KEEP = 16", "KEEP = 32")
STRATEGY = (ROOT / ".venv-official" / "lib" / "python3.12" / "site-packages" / "skydiscover" / "optimize" /
            "search" / "evox" / "database" / "initial_search_strategy.py").read_text()
VARIANTS = [1, 2, 3]
PATTERN = re.compile(r"MOCK_VARIANT = (\d+)")
LOG = Path(sys.argv[2])
CAPTURE = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def with_knob(source, k):
    return source.replace("\n\ndef certify(family):", f"\n\nMOCK_VARIANT = {k}\n\n\ndef certify(family):", 1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            return self.reply(404, {"error": "not found"})
        return self.reply(200, {"object": "list", "data": [{"id": "gemini-3.8-flash", "object": "model"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        text = json.dumps(body.get("messages", []))
        role = self.headers.get("X-LRX-Call-Role", "")
        if CAPTURE:
            CAPTURE.mkdir(parents=True, exist_ok=True)
            index = len(list(CAPTURE.glob("request-*.json"))) + 1
            (CAPTURE / f"request-{index:04d}.json").write_text(json.dumps({"role": role, "body": body}))
        plain = text.replace('\\"', '"').replace("\\'", "'")
        cut = plain.find("## Program Information")
        found = PATTERN.findall(plain[cut:] if cut >= 0 else plain)
        current = int(found[0]) if found else None
        nxt = VARIANTS[(VARIANTS.index(current) + 1) % len(VARIANTS)] if current in VARIANTS else 2
        if "EvolvedProgramDatabase" in text and ("database" in text.lower() or "search algorithm" in text.lower()):
            kind, content = "strategy", "```python\n" + STRATEGY + "\n```"
        elif "variation operator" in text.lower() or "diverge" in text.lower():
            kind, content = "variation", "Try fewer X letters on zero blocks."
        elif "certify" not in plain:
            kind, content = "probe", "OK"
        elif role in ("gepa_reflection", "sequential_refinement"):
            kind = "solution_full"
            content = "Here is the program.\n```python\n" + with_knob(SWEEP if nxt == 2 else NAIVE, nxt) + "```\n"
        elif current is None:
            kind = "solution_diff"
            content = ("<<<<<<< SEARCH\ndef certify(family):\n=======\nMOCK_VARIANT = %d\n\n\ndef certify(family):\n"
                       ">>>>>>> REPLACE" % nxt)
        else:
            kind = "solution_diff"
            content = f"<<<<<<< SEARCH\nMOCK_VARIANT = {current}\n=======\nMOCK_VARIANT = {nxt}\n>>>>>>> REPLACE"
        marks = text.count("BOUND_PACKET_V1")
        with LOG.open("a") as log:
            log.write(json.dumps({"t": time.time(), "kind": kind, "role": role, "packet_seen": marks > 0,
                                  "packet_count": marks, "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "request_chars": len(text), "max_tokens": body.get("max_tokens"),
                                  "reasoning_effort": body.get("reasoning_effort"), "m11_seen": "m11-" in text,
                                  "current_variant": current, "proposed_variant": nxt}) + "\n")
        return self.reply(200, {"id": f"mock-{time.time_ns()}", "object": "chat.completion",
                                "created": int(time.time()), "model": body.get("model", "gemini-3.8-flash"),
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
