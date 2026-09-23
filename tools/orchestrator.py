"""Helpers for the Claude autoresearch orchestrator (see autoresearch/PROGRAM.md).

    python tools/orchestrator.py score            # Verify: best train score among leads (one number)
    python tools/orchestrator.py promote RUN_DIR  # copy a run's best candidate to candidates/leads/ if it beats all leads
    python tools/orchestrator.py spend            # Guard: exit 1 if logged spend exceeds LRX_MAX_TOTAL_USD (default 20)
    python tools/orchestrator.py status           # leads, spend, last runs (JSON)
    python tools/orchestrator.py ratio            # Verify (proof progress): best sound lead's
                                                  # max over m>=8 train graphs of max_word / T
    python tools/orchestrator.py trusted          # Guard: trusted core unchanged (hash lock)
    python tools/orchestrator.py lock-trusted     # HUMAN ONLY: re-lock after reviewed changes

Scores come from the deterministic evaluator (train split). Held-out scores are
printed by `status` for the human only and never used for promotion.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lrx.candidates import Candidate  # noqa: E402
from src.lrx.evaluator import evaluate  # noqa: E402

LEADS = ROOT / "candidates" / "leads"
RUNS = ROOT / "runs"
TRUSTED_LOCK = ROOT / "autoresearch" / "trusted.lock.json"
# Everything that decides truth, scores, data or money. The orchestrator may
# change search-side code (engines, proposers, prompts, feedback, reports) but
# never these files; `trusted` fails if any hash differs from the lock.
TRUSTED = [
    "AGENTS.md",
    "src/lrx/state.py",
    "src/lrx/table_bfs.py",
    "src/lrx/certificates.py",
    "src/lrx/reference_bfs.py",
    "src/lrx/exact_dp.py",
    "src/lrx/evaluate.py",
    "src/lrx/evaluator.py",
    "src/lrx/dsl.py",
    "src/lrx/candidates.py",
    "src/lrx/lifting_fast.py",
    "src/lrx/llm.py",
    "src/lrx/cli.py",
    "src/lrx/commands.py",
    "datasets/registry.json",
    "datasets/tables.lock.json",
    "tools/orchestrator.py",
    "tools/verify_lift_independent.py",
    "tools/run_orchestrator.sh",
    "autoresearch/orchestrator.settings.json",
    "tests/fixtures.py",
    "tests/test_bfs.py",
    "tests/test_certificates.py",
    "tests/test_cli.py",
    "tests/test_cli_v2.py",
    "tests/test_dsl_candidates.py",
    "tests/test_evaluator.py",
    "tests/test_exact_dp.py",
    "tests/test_lifting_fast.py",
    "tests/test_safety.py",
    "tests/test_state.py",
    "tests/test_table_bfs.py",
]


def lead_scores():
    rows = []
    for path in sorted(LEADS.glob("*.json")):
        spec = json.loads(path.read_text())
        res = evaluate(spec, split="train")
        rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "score": res["score"],
                "feasible": res["feasible"],
                "kind": res.get("kind"),
            }
        )
    return rows


def best_score():
    rows = lead_scores()
    return max((r["score"] for r in rows), default=-1e6)


def logged_spend():
    total = 0.0
    for summary in RUNS.glob("*/summary.json"):
        try:
            data = json.loads(summary.read_text())
        except ValueError:
            continue
        usage = data.get("usage") or {}
        total += usage.get("estimated_usd") or data.get("usd") or 0.0
        total += (usage.get("reflector") or {}).get("estimated_usd") or 0.0
    return round(total, 4)


def _sha(path):
    import hashlib

    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def trusted_status():
    lock = json.loads(TRUSTED_LOCK.read_text()) if TRUSTED_LOCK.exists() else {}
    changed = [p for p in TRUSTED if lock.get(p) != _sha(p)]
    missing = [p for p in TRUSTED if p not in lock]
    return {
        "ok": not changed and set(lock) == set(TRUSTED),
        "changed": changed,
        "missing_from_lock": missing,
    }


def lead_ratio():
    """Proof-progress metric: min over sound leads of max_{m>=8 train} value/T.

    1.0 means the best lead stays within the conjectured budget on every m>=8
    train graph's probes. Leads with any failure are ignored. Lower is better.
    """
    best = None
    for path in sorted(LEADS.glob("*.json")):
        res = evaluate(json.loads(path.read_text()), split="train")
        graphs = [g for g in res.get("graphs", []) if g.get("feedback")]
        if (
            not res.get("valid")
            or res.get("stopped")
            or any(g["failures"] or g.get("incomplete") for g in graphs)
        ):
            continue
        ratios = [g["value_max"] / g["T"] for g in graphs if g["T_applies"]]
        if ratios:
            worst = max(ratios)
            best = worst if best is None else min(best, worst)
    return round(best, 4) if best is not None else 99.0


def promote(run_dir):
    best = Path(run_dir) / "best.json"
    if not best.exists():
        return {"promoted": False, "reason": "run has no best.json"}
    spec = json.loads(best.read_text())
    cand = Candidate(spec)
    score = evaluate(spec, split="train")["score"]
    current = best_score()
    if score <= current:
        return {"promoted": False, "score": score, "best_lead": current}
    spec["notes"] = (spec.get("notes", "") + f" | Promoted from {Path(run_dir).name}.")[
        :2000
    ]
    out = LEADS / f"{cand.hash}.json"
    if out.exists():
        return {"promoted": False, "reason": "already a lead", "path": str(out)}
    out.write_text(json.dumps(spec, indent=1) + "\n")
    return {
        "promoted": True,
        "score": score,
        "previous_best": current,
        "path": str(out.relative_to(ROOT)),
    }


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "score":
        print(best_score())
        return 0
    if cmd == "ratio":
        print(lead_ratio())
        return 0
    if cmd == "trusted":
        st = trusted_status()
        print(json.dumps(st))
        return 0 if st["ok"] else 1
    if cmd == "lock-trusted":
        if os.environ.get("LRX_HUMAN_LOCK") != "yes":
            print("refused: set LRX_HUMAN_LOCK=yes (human review only)")
            return 2
        TRUSTED_LOCK.write_text(
            json.dumps({p: _sha(p) for p in TRUSTED}, indent=1) + "\n"
        )
        print(json.dumps(trusted_status()))
        return 0
    if cmd == "promote":
        print(json.dumps(promote(argv[1])))
        return 0
    if cmd == "spend":
        limit = float(os.environ.get("LRX_MAX_TOTAL_USD", "20"))
        spent = logged_spend()
        print(json.dumps({"logged_usd": spent, "limit_usd": limit}))
        return 0 if spent <= limit else 1
    if cmd == "status":
        runs = sorted(RUNS.glob("*/summary.json"), key=lambda p: p.stat().st_mtime)[-5:]
        print(
            json.dumps(
                {
                    "leads": lead_scores(),
                    "logged_usd": logged_spend(),
                    "recent_runs": [p.parent.name for p in runs],
                },
                indent=1,
            )
        )
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
