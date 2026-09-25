"""Control (b) for Track 3: a deterministic, LLM-free tactic sweep (the floor for engine claims).

For each tactic in a fixed list, one body states every target and milestone as
`theorem <id> : Stmt.<id> := by unfold Stmt.<id>; <tactic>` and is scored by the
trusted evaluator (failing blocks are pruned, so each id is judged separately).
The union of closed ids over all tactics is the floor. No model call is made.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrations import lean_evaluator as E
from integrations import lean_task as T

SIMP_SET = "exec, step, inv, rotL, rotR, swap12, freeReduce, push, proj, track, keep, rep, macroZL, macroLZ, root"
TACTICS = (
    "rfl",
    "decide",
    "omega",
    f"simp [{SIMP_SET}]",
    "intros; simp_all [exec, List.foldl_append]",
    f"intro x\n  induction x <;> intros <;> simp_all [{SIMP_SET}, List.foldl_append]",
    "grind",
    f"grind [{SIMP_SET}, List.foldl_append]",
    "exact?",
)


def body_for(tactic: str) -> str:
    parts = [f"-- tactic sweep control: {tactic.splitlines()[0]}"]
    for i in T.IDS:
        parts += [f"theorem {i} : Stmt.{i} := by", f"  unfold Stmt.{i}", f"  {tactic}", ""]
    return "\n".join(parts)


def sweep(cache_dir=None) -> dict:
    rows, union = [], set()
    for tactic in TACTICS:
        res = E.evaluate(body_for(tactic), cache_dir=cache_dir)
        closed = [i for i in T.IDS if res["statuses"].get(i) == "closed"]
        union |= set(closed)
        rows.append({"tactic": tactic, "status": res["status"], "closed": closed,
                     "combined_score": res["combined_score"], "seconds": res.get("seconds"),
                     "passes": len(res.get("passes", []))})
    return {"control": "tactic-sweep", "evaluator_version": E.VERSION, "lock_digest": T.verify_lock(),
            "toolchain": E.check_toolchain(), "tactics": rows,
            "closed_union": [i for i in T.IDS if i in union],
            "closed_targets": [i for i in T.TARGETS if i in union],
            "closed_milestones": [i for i in T.MILESTONES if i in union]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit(f"{args.output} exists; use a fresh path")
    out = sweep(args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("closed_union", "closed_targets", "closed_milestones")}))


if __name__ == "__main__":
    main()
