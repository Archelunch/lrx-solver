"""Offline responder for the post-fix lift smoke (autoresearch/SMOKE-FIXED-260925.md).

Usage: python mock_api_fixed.py PORT LOG.jsonl [CAPTURE_DIR]
Same dispatch as mock_api.py (SkyDiscover diff/strategy/variation/probe paths
are untouched -- those are not in scope for the preflight_source fix). For
GEPA reflection and sequential-refinement calls only, cycles every 4th call
through: (1) a plain single fence, (2) prose before/after a single fence,
(3) two fenced blocks where only the LAST defines lift(...), (4) a truncated
response (finish_reason=length, no closing fence) that must be rejected.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SEED = (ROOT / "integrations" / "lift_control_naive.py").read_text()
STRATEGY = (ROOT / ".venv-official" / "lib" / "python3.12" / "site-packages" / "skydiscover" / "optimize" /
            "search" / "evox" / "database" / "initial_search_strategy.py").read_text().replace(
    "parent = self.rng.choice(candidates)",
    "if self.name == 'evox': print('MOCK_STRATEGY_SAMPLE_USED')\n"
    "            parent = max(candidates, key=lambda p: float(p.metrics.get('combined_score', 0) or 0))  # MOCK_STRATEGY_REWRITE")
VARIANTS = ["('short',)", "('short', 'right', 'left')", "('short', 'right')", "('short', 'left')"]
PATTERN = re.compile(r"DIRECTIONS = (\([^)\n]*\))")
LOG = Path(sys.argv[2])
CAPTURE = Path(sys.argv[3]) if len(sys.argv) > 3 else None
CALL_COUNTS = {}


def _solution_body(nxt):
    return SEED.replace("DIRECTIONS = ('short',)", "DIRECTIONS = " + nxt)


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
        cut = plain.find("## Program Information")
        found = PATTERN.findall(plain[cut:] if cut >= 0 else plain)
        current = found[0] if found else VARIANTS[0]
        nxt = VARIANTS[(VARIANTS.index(current) + 1) % len(VARIANTS)] if current in VARIANTS else VARIANTS[1]
        finish_reason = "stop"
        if "EvolvedProgramDatabase" in text and ("database" in text.lower() or "search algorithm" in text.lower()):
            kind, content = "strategy", "```python\n" + STRATEGY + "\n```"
        elif "variation operator" in text.lower() or "diverge" in text.lower():
            kind, content = "variation", "Try other bubble directions for the new label and other parent rows."
        elif "DIRECTIONS" not in plain:
            kind, content = "probe", "OK"
        elif role in ("gepa_reflection", "sequential_refinement"):
            CALL_COUNTS[role] = CALL_COUNTS.get(role, 0) + 1
            slot = CALL_COUNTS[role] % 4
            solution = _solution_body(nxt)
            if slot == 1:
                kind, content = "solution_full_plain", "```python\n" + solution + "```"
            elif slot == 2:
                kind = "solution_full_prose"
                content = ("Here is the improved program:\n```python\n" + solution +
                          "```\nI changed DIRECTIONS as requested.")
            elif slot == 3:
                kind = "solution_full_multifence"
                scratch = "```python\n# scratch, not a real answer\nx = 1\n```\n"
                content = "Let me think first.\n" + scratch + "\nHere is the answer:\n```python\n" + solution + "```"
            else:
                kind = "solution_full_truncated"
                finish_reason = "length"
                # No closing fence: a genuinely truncated model output.
                content = "```python\n" + solution[:len(solution) // 2]
        else:
            kind = "solution_diff"
            content = f"<<<<<<< SEARCH\nDIRECTIONS = {current}\n=======\nDIRECTIONS = {nxt}\n>>>>>>> REPLACE"
        marks = text.count("LIFT_PACKET_V1")
        with LOG.with_suffix(".texts.jsonl").open("a") as dump:
            dump.write(json.dumps({"kind": kind, "role": role, "text": plain}) + "\n")
        with LOG.open("a") as log:
            log.write(json.dumps({"t": time.time(), "kind": kind, "role": role, "packet_seen": marks > 0,
                                  "packet_count": marks, "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "request_chars": len(text), "max_tokens": body.get("max_tokens"),
                                  "reasoning_effort": body.get("reasoning_effort"),
                                  "finish_reason": finish_reason,
                                  "current_directions": current if kind.startswith("solution") else None,
                                  "proposed_directions": nxt if kind.startswith("solution") else None}) + "\n")
        return self.reply(200, {"id": f"mock-{time.time_ns()}", "object": "chat.completion",
                                "created": int(time.time()), "model": body.get("model", "grok-4.7"),
                                "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                             "finish_reason": finish_reason}],
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
