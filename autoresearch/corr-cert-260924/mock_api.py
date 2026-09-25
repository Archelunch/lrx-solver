"""Offline OpenAI-compatible responder for corr-cert engine smokes (no provider calls).

Usage: python mock_api.py PORT LOG.jsonl [CAPTURE_DIR]
Modeled on autoresearch/lift-m9-260924/mock_api.py. Solutions change only the
MULT knob of the seed (integrations/corr_control_f1.py), so every proposal is
a real, valid coefficients(m) program (it just still fails the certificate --
this is an offline mechanism smoke, not a search for a real fix). GEPA and
the sequential control get full fenced source. SkyDiscover gets a
SEARCH/REPLACE diff. EvoX strategy requests get the upstream initial strategy
with a logged marker, as in the official-integration mock. Every request is
logged with whether the corr-cert feedback packet was present.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SEED = (ROOT / "integrations" / "corr_control_f1.py").read_text()
STRATEGY = (ROOT / ".venv-official" / "lib" / "python3.12" / "site-packages" / "skydiscover" / "optimize" /
            "search" / "evox" / "database" / "initial_search_strategy.py").read_text().replace(
    "parent = self.rng.choice(candidates)",
    "if self.name == 'evox': print('MOCK_STRATEGY_SAMPLE_USED')\n"
    "            parent = max(candidates, key=lambda p: float(p.metrics.get('combined_score', 0) or 0))  # MOCK_STRATEGY_REWRITE")
VARIANTS = [3, 4, 5, 6]
PATTERN = re.compile(r"MULT = (-?\d+)")
LOG = Path(sys.argv[2])
CAPTURE = Path(sys.argv[3]) if len(sys.argv) > 3 else None  # exact request bodies, for first-prompt.md


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            return self.reply(404, {"error": "not found"})
        return self.reply(200, {"object": "list", "data": [{"id": "grok-4.7", "object": "model"}]})

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
        cut = plain.find("## Program Information")  # SkyDiscover: the parent source follows this header
        found = PATTERN.findall(plain[cut:] if cut >= 0 else plain)
        current = int(found[0]) if found else VARIANTS[0]
        nxt = VARIANTS[(VARIANTS.index(current) + 1) % len(VARIANTS)] if current in VARIANTS else VARIANTS[1]
        if "EvolvedProgramDatabase" in text and ("database" in text.lower() or "search algorithm" in text.lower()):
            kind, content = "strategy", "```python\n" + STRATEGY + "\n```"
        elif "variation operator" in text.lower() or "diverge" in text.lower():
            kind, content = "variation", "Try other MULT constants and other bump placements."
        elif "MULT" not in plain:
            kind, content = "probe", "OK"  # upstream connectivity checks carry no program
        elif role in ("gepa_reflection", "sequential_refinement"):
            kind = "solution_full"
            content = "```python\n" + SEED.replace("MULT = 4", "MULT = %d" % nxt) + "```"
        else:
            kind = "solution_diff"
            content = f"<<<<<<< SEARCH\nMULT = {current}\n=======\nMULT = {nxt}\n>>>>>>> REPLACE"
        marks = text.count("CORR_PACKET_V1")
        with LOG.with_suffix(".texts.jsonl").open("a") as dump:  # offline fixture debugging only
            dump.write(json.dumps({"kind": kind, "role": role, "text": plain}) + "\n")
        with LOG.open("a") as log:
            log.write(json.dumps({"t": time.time(), "kind": kind, "role": role, "packet_seen": marks > 0,
                                  "packet_count": marks, "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "request_chars": len(text), "max_tokens": body.get("max_tokens"),
                                  "reasoning_effort": body.get("reasoning_effort"),
                                  "current_mult": current if kind.startswith("solution") else None,
                                  "proposed_mult": nxt if kind.startswith("solution") else None}) + "\n")
        return self.reply(200, {"id": f"mock-{time.time_ns()}", "object": "chat.completion",
                                "created": int(time.time()), "model": body.get("model", "grok-4.7"),
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
