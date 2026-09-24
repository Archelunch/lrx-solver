"""Two-round native GEPA integration receipt using a local mock model only."""

import argparse
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integrations import official_backends as official
from integrations.research_budget import Broker, DurableBudget


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *_args):
        return json.dumps(self.payload).encode()


class FakeOpener:
    def __init__(self, source):
        self.source = source
        self.calls = 0

    def open(self, request, timeout):
        if request.full_url != "https://api.example.com/v1/chat/completions":
            raise AssertionError(request.full_url)
        self.calls += 1
        candidate = self.source + f"\n# Offline protocol fixture {self.calls}\n"
        return FakeResponse({
            "model": "grok-4.7",
            "choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": "```python\n" + candidate + "\n```"}}],
            "usage": {"prompt_tokens": 2000, "completion_tokens": 100},
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    frozen = Path(__file__).parent / "frozen"
    archive = args.run_dir.parent / (args.run_dir.name + "-mock-archive.sqlite")
    if archive.exists():
        raise FileExistsError(archive)
    shutil.copyfile(Path(__file__).parent / "development-archive.sqlite", archive)
    ledger = args.run_dir.parent / (args.run_dir.name + "-mock-ledger.json")
    if ledger.exists():
        raise FileExistsError(ledger)
    budget = DurableBudget(ledger, max_requests=2, max_usd=1,
                           input_rate=1, output_rate=1)
    broker = Broker(("127.0.0.1", 0), upstream_url="https://api.example.com/v1",
                    model="grok-4.7", api_key_env="LRX_OFFLINE_MOCK_KEY", ledger=budget,
                    max_tokens=4096, reasoning_reserve=0, timeout=30)
    thread = threading.Thread(target=broker.serve_forever, daemon=True)
    thread.start()
    fake = FakeOpener((frozen / "allcuts_seed.py").read_text())
    run_args = official._parser().parse_args([
        "run", "--engine", "gepa", "--seed", str(frozen / "allcuts_seed.py"),
        "--cases", str(frozen / "development.json"),
        "--baseline", str(frozen / "development-baseline.json"),
        "--incumbent", str(frozen / "development-incumbent.json"),
        "--dual", str(frozen / "development-dual.json"),
        "--run-dir", str(args.run_dir),
        "--broker-url", f"http://127.0.0.1:{broker.server_port}/v1",
        "--model", "grok-4.7", "--iterations", "2", "--max-tokens", "4096",
        "--llm-timeout", "30", "--wall-seconds", "120", "--max-evals", "100",
        "--reasoning-effort", "low", "--archive", str(archive),
        "--archive-query", "k5-mask302-order15713", "--archive-limit", "1",
        "--research-context", str(Path(__file__).parent / "development-context.txt"),
    ])
    try:
        with patch.dict(os.environ, {"LRX_OFFLINE_MOCK_KEY": "offline-secret"}), \
             patch("urllib.request.build_opener", return_value=fake):
            manifest = official._launch(run_args)
    finally:
        broker.shutdown()
        broker.server_close()
        thread.join(timeout=5)
        budget.close()
    run_log = json.loads((args.run_dir / "output" / "gepa" / "run_log.json").read_text())
    summary = json.loads((args.run_dir / "output" / "summary.json").read_text())
    receipt_paths = [row["receipt_path"] for row in json.loads(ledger.read_text())["attempts"]]
    report = {
        "run_dir": str(args.run_dir), "model_calls": fake.calls,
        "sampled_case_ids": [[official._load_cases(frozen / "development.json")[i]["id"]
                              for i in item["subsample_ids"]] for item in run_log],
        "hard_case_ids": summary["mandatory_hard_case_ids"],
        "reflection_batch_calls": summary["reflection_batch_calls"],
        "context_receipts": summary["context_receipts"],
        "broker_receipts": receipt_paths,
        "manifest_research_status": manifest["research_status"],
        "manifest_status": manifest["status"],
    }
    (args.run_dir / "offline-smoke-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
