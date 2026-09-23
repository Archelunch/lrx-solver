"""Run one authorized session config, preserving live usage on interruption."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.lrx.evolve import Campaign, build_proposer
from tools.orchestrator import trusted_status


class GuardedCampaign(Campaign):
    failures_in_a_row = 0

    def finish(self, req, out, result):
        improved = super().finish(req, out, result)
        error = out.get("error") or ""
        infrastructure = error.startswith(("URLError", "HTTPError", "TimeoutError",
            "ConnectionError", "RequestAborted", "OSError", "ValueError: response usage",
            "ValueError: provider"))
        self.failures_in_a_row = self.failures_in_a_row + 1 if infrastructure else 0
        if self.failures_in_a_row >= 2:
            self.stop_reason = "two consecutive infrastructure failures"
        return improved

    def log_batch(self, *args):
        super().log_batch(*args)
        usage = self.proposer.usage()
        (self.run_dir / "live-usage.json").write_text(json.dumps(usage, indent=2))
        if not trusted_status()["ok"]:
            self.stop_reason = "trusted core changed"
        if usage["estimated_usd"] >= usage["max_spend_usd"]:
            self.stop_reason = "spend cap reached"


def main():
    config = Path(sys.argv[1])
    cfg = json.loads(config.read_text())
    if not trusted_status()["ok"]:
        raise RuntimeError("trusted core changed before run")
    # Fixed per-run caps leave a reserve under the user's total $50 ceiling.
    if cfg["provider"]["max_spend_usd"] > 6 or cfg.get("reflector"):
        raise ValueError("session requires one shared ledger capped at $6")
    run_dir = config.parent / (config.stem + "-run")
    proposer = build_proposer(cfg, allow_network=True)
    campaign = GuardedCampaign(cfg, run_dir, proposer)
    try:
        summary = campaign.run()
    finally:
        (run_dir / "final-usage.json").write_text(json.dumps(proposer.usage(), indent=2))
    print(json.dumps({k: summary.get(k) for k in (
        "engine", "stop_reason", "proposals", "valid_proposals", "usage", "wall_seconds")}))


if __name__ == "__main__":
    main()
