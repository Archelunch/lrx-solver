"""Offline OpenAI-compatible responder for pinned upstream optimizer smoke runs."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
SEED = (ROOT / "integrations" / "program_seed.py").read_text()
STRATEGY = (ROOT / ".venv-official" / "lib" / "python3.12" / "site-packages" /
            "skydiscover" / "optimize" / "search" / "evox" / "database" /
            "initial_search_strategy.py").read_text()
STRATEGY = STRATEGY.replace(
    "parent = self.rng.choice(candidates)",
    "if self.name == 'evox': print('MOCK_STRATEGY_SAMPLE_USED')\n"
    "            parent = max(candidates, key=lambda p: float(p.metrics.get('combined_score', 0) or 0))  # MOCK_STRATEGY_REWRITE",
)
LOG = Path(sys.argv[2])


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            return self.reply(404, {"error": "not found"})
        return self.reply(200, {"object": "list", "data": [{"id": "grok-4.7", "object": "model"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        text = json.dumps(body.get("messages", []))
        if "EvolvedProgramDatabase" in text and ("database" in text.lower() or "search algorithm" in text.lower()):
            kind, content = "strategy", "```python\n" + STRATEGY + "\n```"
        elif "variation operator" in text.lower() or "diverge" in text.lower():
            kind, content = "variation", "Explore different cut positions and L/R routing to find shorter valid sorting words."
        else:
            kind, content = "solution", (
                "<<<<<<< SEARCH\n    return words\n=======\n"
                "    return words\n# MOCK_SOLUTION_REWRITE\n>>>>>>> REPLACE"
            )
        with LOG.open("a") as log:
            log.write(json.dumps({"kind": kind, "fields": sorted(body),
                                  "max_tokens": body.get("max_tokens"),
                                  "archive_raw_trace_seen": "RAW_TRACE_ARCHIVE_MARKER" in text,
                                  "archive_source_diff_seen": "--- parent" in text,
                                  "response_has_strategy_marker": "MOCK_STRATEGY_REWRITE" in content}) + "\n")
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
