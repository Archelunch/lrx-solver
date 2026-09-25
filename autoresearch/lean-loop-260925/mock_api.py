"""Offline OpenAI-compatible responder for Track 3 engine smokes (no provider calls).

Usage: python mock_api.py PORT LOG.jsonl [CAPTURE_DIR]
Modeled on autoresearch/sort-m9-260925/mock_api.py. Every proposal is a full Lean
body in one ```lean block with a comment knob `-- MOCK_VARIANT = k`:
1 = the sorry-stub seed, 2 = stubs plus real proofs of M1 and M2 (an accepted
improvement), 3 = variant 2 plus one broken helper theorem (exercises error
pruning and error packets). No reference proof is used. Requests are logged with
whether the evaluator packet was present, and optionally captured verbatim.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integrations.lean_task import seed_body  # noqa: E402

M1 = """theorem M1 : Stmt.M1 := by
  intro p s v
  simp only [exec, List.foldl_append]
"""
M2 = """theorem M2 : Stmt.M2 := by
  intro g v
  cases g
  · cases v with
    | nil => rfl
    | cons a t => simp [step, inv, rotL, rotR]
  · rcases List.eq_nil_or_concat v with h | ⟨L, b, h⟩
    · subst h; rfl
    · subst h; simp [step, inv, rotL, rotR]
  · match v with
    | [] => rfl
    | [_] => rfl
    | _ :: _ :: _ => rfl
"""
BROKEN = """theorem broken_helper (v : List Nat) : rotL v = v := by
  simp [rotL]
"""
VARIANTS = [1, 2, 3]
PATTERN = re.compile(r"MOCK_VARIANT = (\d+)")
LOG = Path(sys.argv[2])
CAPTURE = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def body(k):
    text = seed_body()
    if k >= 2:
        text = text.replace("theorem M1 : Stmt.M1 := by\n  unfold Stmt.M1\n  sorry\n", M1)
        text = text.replace("theorem M2 : Stmt.M2 := by\n  unfold Stmt.M2\n  sorry\n", M2)
    if k == 3:
        text = BROKEN + "\n" + text
    return f"-- MOCK_VARIANT = {k}\n" + text


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            return self.reply(404, {"error": "not found"})
        return self.reply(200, {"object": "list", "data": [{"id": "gemini-3.8-flash", "object": "model"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "not found"})
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        text = json.dumps(req.get("messages", []))
        role = self.headers.get("X-LRX-Call-Role", "")
        if CAPTURE:
            CAPTURE.mkdir(parents=True, exist_ok=True)
            index = len(list(CAPTURE.glob("request-*.json"))) + 1
            (CAPTURE / f"request-{index:04d}.json").write_text(json.dumps({"role": role, "body": req}))
        found = PATTERN.findall(text)
        current = int(found[-1]) if found else 1
        nxt = VARIANTS[(VARIANTS.index(current) + 1) % len(VARIANTS)] if current in VARIANTS else 2
        if "Stmt." not in text:
            kind, content = "probe", "OK"
        else:
            kind, content = "solution_full", "```lean\n" + body(nxt) + "```\n"
        marks = text.count("LEAN_PACKET_V1")
        with LOG.open("a") as log:
            log.write(json.dumps({"t": time.time(), "kind": kind, "role": role, "packet_seen": marks > 0,
                                  "packet_count": marks, "request_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "request_chars": len(text), "max_tokens": req.get("max_tokens"),
                                  "current_variant": current, "proposed_variant": nxt}) + "\n")
        return self.reply(200, {"id": f"mock-{time.time_ns()}", "object": "chat.completion",
                                "created": int(time.time()), "model": req.get("model", "gemini-3.8-flash"),
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
