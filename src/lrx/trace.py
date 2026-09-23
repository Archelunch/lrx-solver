"""Read campaign runs back: lineage, timeline, single-candidate traces.

A run directory holds events.jsonl (one JSON event per line), prompts/ (system
prompts by hash), evals/ (full evaluator results by candidate hash) and
summary.json. This module only reads them.
"""

import json
from pathlib import Path


def load_run(run_dir):
    run_dir = Path(run_dir)
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"no events.jsonl in {run_dir}")
    run = {
        "dir": str(run_dir),
        "name": run_dir.name,
        "start": None,
        "end": None,
        "candidates": [],
        "batches": [],
        "reflections": [],
        "migrations": [],
        "heldout": [],
    }
    for line in events_path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        kind = event.get("event")
        if kind == "start":
            run["start"] = event
        elif kind == "end":
            run["end"] = event
        elif kind == "candidate":
            run["candidates"].append(event)
        elif kind == "batch":
            run["batches"].append(event)
        elif kind == "reflection":
            run["reflections"].append(event)
        elif kind == "migration":
            run["migrations"].append(event)
        elif kind == "heldout":
            run["heldout"].append(event)
    summary = run_dir / "summary.json"
    run["summary"] = json.loads(summary.read_text()) if summary.exists() else None
    run["config"] = (run["start"] or {}).get("config") or _read_json(
        run_dir / "config.json"
    )
    run["complete"] = run["end"] is not None
    return run


def _read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def best_so_far(run):
    """[(proposal_index, best_score)] over non-seed candidates in log order."""
    best, out = None, []
    for index, c in enumerate(run["candidates"]):
        if c.get("valid") and c.get("status") != "duplicate":
            if best is None or c["score"] > best:
                best = c["score"]
        out.append((index, best))
    return out


def children(run):
    """parent id -> children; orphans (parent missing from the log) go under None."""
    ids = {c["id"] for c in run["candidates"]}
    kids = {}
    for c in run["candidates"]:
        parents = c.get("parents") or []
        parent = parents[0] if parents and parents[0] in ids else None
        kids.setdefault(parent, []).append(c)
    return kids


def lineage_lines(run, max_depth=50):
    kids = children(run)
    lines = []

    def walk(node_id, depth):
        for c in kids.get(node_id, []):
            extra = (
                f" +merge #{c['parents'][1]}" if len(c.get("parents") or []) > 1 else ""
            )
            lines.append(
                f"{'  ' * depth}#{c['id']} {c.get('status', '?'):9} "
                f"{_fmt(c.get('score')):>10} {c.get('mode', ''):8} "
                f"isl={c.get('island')} {(c.get('spec') or {}).get('name', '')}{extra}"
            )
            if depth < max_depth:
                walk(c["id"], depth + 1)

    walk(None, 0)
    return lines


def timeline_rows(run):
    rows = []
    for b in run["batches"]:
        usage = b.get("usage") or {}
        rows.append(
            {
                "batch": b["batch"],
                "proposals": b["proposals"],
                "best_score": b.get("best_score"),
                "best_id": b.get("best_id"),
                "since_improvement": b.get("since_improvement"),
                "propose_s": b.get("propose_seconds"),
                "eval_s": b.get("eval_seconds"),
                "usd": usage.get("estimated_usd", 0.0),
                "t": b.get("t"),
            }
        )
    return rows


def candidate_trace(run, cand_id):
    matches = [c for c in run["candidates"] if c["id"] == cand_id]
    if not matches:
        raise KeyError(f"candidate {cand_id} not in run")
    c = dict(matches[0])
    run_dir = Path(run["dir"])
    sha = c.get("prompt_system_sha")
    if sha:
        c["prompt_system_path"] = str(run_dir / "prompts" / f"system-{sha}.txt")
    if c.get("hash"):
        eval_path = run_dir / "evals" / f"{c['hash']}.json"
        if eval_path.exists():
            c["eval_path"] = str(eval_path)
            c["eval"] = json.loads(eval_path.read_text())
    return c


def overview(run):
    """Run summary; computed from events when summary.json is not written yet."""
    summary = run.get("summary") or {}
    cands = run["candidates"]
    statuses = {}
    for c in cands:
        statuses[c.get("status")] = statuses.get(c.get("status"), 0) + 1
    usd = sum(c.get("cost_usd") or 0 for c in cands) + sum(
        r.get("cost_usd") or 0 for r in run["reflections"]
    )
    scored = [c for c in cands if c.get("valid") and c.get("status") != "duplicate"]
    seeds = [c["score"] for c in scored if c.get("mode") == "seed"]
    best = max(scored, key=lambda c: c["score"], default=None)
    last_t = max(
        [e.get("t", 0) for e in cands + run["batches"] + run["reflections"]],
        default=None,
    )
    usage = summary.get("usage") or (
        run["batches"][-1].get("usage") if run["batches"] else {}
    )
    return {
        "run": run["name"],
        "complete": run["complete"],
        "engine": (run["config"] or {}).get("engine"),
        "kinds": (run["config"] or {}).get("kinds"),
        "provider": ((run["config"] or {}).get("provider") or {}).get(
            "model", "offline"
        ),
        "candidates": len(cands),
        "proposals": summary.get(
            "proposals", sum(1 for c in cands if c.get("mode") != "seed")
        ),
        "statuses": statuses,
        "batches": len(run["batches"]),
        "reflections": len(run["reflections"]),
        "seed_best": summary.get("seed_best", max(seeds, default=None)),
        "best": (summary.get("best") or {}).get(
            "score", best["score"] if best else None
        ),
        "best_id": (summary.get("best") or {}).get("id", best["id"] if best else None),
        "feasible": (summary.get("best") or {}).get(
            "feasible_on_train_probes", best.get("feasible") if best else None
        ),
        "usage": usage or {},
        "usd_logged": round(usd, 6),
        "stop_reason": summary.get("stop_reason"),
        "wall_seconds": summary.get("wall_seconds", last_t),
    }


def _fmt(x):
    return "-" if x is None else f"{x:.2f}" if isinstance(x, float) else str(x)
