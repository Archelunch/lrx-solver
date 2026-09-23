"""Compact read-only campaign audit; no held-out feedback or paid requests."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.lrx.trace import load_run


def main():
    directory = Path(__file__).parent
    rows = []
    for path in sorted(directory.glob("*-run")):
        run = load_run(path)
        candidates = run["candidates"]
        proposals = [c for c in candidates if c.get("mode") != "seed"]
        latest = run["batches"][-1] if run["batches"] else {}
        summary = run["summary"] or {}
        usage = summary.get("usage") or latest.get("usage") or {}
        evals = {}
        cache_hits, cached_source_seconds = 0, 0.0
        for c in candidates:
            key = c.get("hash")
            f = path / "evals" / f"{key}.json"
            if key and f.exists() and key not in evals:
                e = json.loads(f.read_text())
                if e.get("cache_hit"):
                    cache_hits += 1
                    cached_source_seconds += e.get("source_seconds") or 0
                graphs = [g for g in e.get("graphs", []) if g.get("feedback")]
                if e.get("stopped") or any(g.get("failures") or g.get("incomplete") for g in graphs):
                    evals[key] = None
                else:
                    evals[key] = max((g["value_max"] / g["T"] for g in graphs
                        if g.get("m", 0) >= 8 and g.get("value_max") is not None), default=None)
        best_id = (summary.get("best") or {}).get("id", latest.get("best_id", 0))
        best = next((c for c in candidates if c["id"] == best_id), {})
        costs = {}
        for dollars in (1, 2, 3, 4, 5, 6):
            eligible = [b for b in run["batches"] if b["usage"]["estimated_usd"] <= dollars]
            chosen = eligible[-1]["best_id"] if eligible else 0
            c = next((c for c in candidates if c["id"] == chosen), {})
            costs[str(dollars)] = evals.get(c.get("hash"))
        rows.append({
            "run": path.name, "complete": run["complete"], "engine": run["config"]["engine"],
            "seed": run["config"]["seed"], "proposals": len(proposals),
            "budget_denied_before_request": sum(
                not c.get("attempts") and (c.get("proposer_error") or "").startswith("BudgetExhausted")
                for c in proposals),
            "valid": sum(bool(c.get("valid")) for c in proposals),
            "fully_solved_proposals": sum(evals.get(c.get("hash")) is not None for c in proposals),
            "repair_calls": sum(c.get("repairs_used") or 0 for c in proposals),
            "duplicates": sum(c.get("status") == "duplicate" for c in proposals),
            "best_hash": best.get("hash"), "best_ratio": evals.get(best.get("hash")),
            "best_score": best.get("score"), "usd": usage.get("estimated_usd", 0),
            "requests": usage.get("requests", 0), "failed_requests": usage.get("failed_requests", 0),
            "usage_overruns": usage.get("usage_overruns", 0),
            "provider_costed_requests": usage.get("provider_costed_requests", 0),
            "billing_verified": usage.get("billing_verified", False),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "reflections": len(run["reflections"]),
            "strategy_changes": sum(bool(r.get("strategy")) for r in run["reflections"]),
            "stop_reason": summary.get("stop_reason"),
            "wall_seconds": summary.get("wall_seconds"),
            "evaluation_wall_seconds": sum(b["eval_seconds"] for b in run["batches"]),
            "cache_hits": cache_hits,
            "cached_source_seconds": cached_source_seconds,
            "best_ratio_by_completed_batch_usd": costs,
            "errors": [c["proposer_error"] for c in proposals if c.get("proposer_error")],
        })
    result = {"runs": rows, "settled_usd": sum(r["usd"] for r in rows),
              "all_complete": bool(rows) and all(r["complete"] for r in rows),
              "note": "Active-run usage is a lower bound until requests settle. Cost curves are completed-round checkpoints."}
    (directory / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(json.dumps({k: row[k] for k in ("run", "proposals", "best_ratio", "usd", "strategy_changes", "complete")}))
    print(json.dumps({"settled_usd": result["settled_usd"], "all_complete": result["all_complete"]}))


if __name__ == "__main__":
    main()
