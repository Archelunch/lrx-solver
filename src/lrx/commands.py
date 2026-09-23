"""v2 CLI commands: tables, candidate evaluation, campaigns, leaderboard.

All output is JSON on stdout. Exit codes: 0 ok, 1 check failed, 2 invalid
input / incomplete / refused.
"""

import argparse
import json
from pathlib import Path

COMMANDS = (
    "table",
    "eval",
    "certify",
    "features",
    "evolve",
    "prompt",
    "leaderboard",
    "llm-smoke",
    "trace",
    "report",
    "lift",
)


def _load_json(path):
    return json.loads(Path(path).read_text())


def main(argv):
    parser = argparse.ArgumentParser(prog="lrx")
    sub = parser.add_subparsers(dest="command", required=True)

    table = sub.add_parser("table", help="ranked BFS distance tables")
    tsub = table.add_subparsers(dest="action", required=True)
    build = tsub.add_parser("build")
    build.add_argument("m", type=int)
    build.add_argument("r", type=int)
    build.add_argument("--out", default="datasets/generated")
    build.add_argument("--workers", type=int, default=1)
    build.add_argument("--max-bytes", type=int, default=2 * 1024**3)
    reg = tsub.add_parser("build-registry")
    reg.add_argument("--workers", type=int, default=1)
    tsub.add_parser("verify")

    ev = sub.add_parser("eval", help="score a candidate JSON file")
    ev.add_argument("candidate")
    ev.add_argument("--split", choices=["sanity", "train", "heldout"], default="train")
    ev.add_argument("--full", action="store_true", help="print full result")
    ev.add_argument("--feedback", action="store_true", help="print proposer feedback")

    cert = sub.add_parser(
        "certify", help="exhaustive bound/potential check on one table"
    )
    cert.add_argument("candidate")
    cert.add_argument("m", type=int)
    cert.add_argument("r", type=int)

    feat = sub.add_parser("features")
    feat.add_argument("m", type=int)
    feat.add_argument("r", type=int)
    feat.add_argument("--v", required=True, help="comma-separated vector")

    evo = sub.add_parser("evolve", help="run a campaign config")
    evo.add_argument("config")
    evo.add_argument("--run-dir")
    evo.add_argument("--allow-network", action="store_true")
    evo.add_argument("--max-proposals", type=int)
    evo.add_argument("--engine")
    evo.add_argument("--seed", type=int)

    pr = sub.add_parser("prompt", help="print the prompt a campaign would send")
    pr.add_argument("config")

    lb = sub.add_parser("leaderboard", help="summarise runs/*/summary.json")
    lb.add_argument("--runs", default="runs")

    smoke = sub.add_parser("llm-smoke", help="one live request (paid)")
    smoke.add_argument("config")
    smoke.add_argument("--allow-network", action="store_true")

    tr = sub.add_parser(
        "trace", help="inspect a run: overview, tree, timeline, one candidate"
    )
    tr.add_argument("run")
    view = tr.add_mutually_exclusive_group()
    view.add_argument("--tree", action="store_true", help="lineage tree (text)")
    view.add_argument("--timeline", action="store_true", help="per-batch progress")
    view.add_argument(
        "--show", type=int, metavar="ID", help="full trace of one candidate"
    )
    view.add_argument(
        "--follow", action="store_true", help="stream new events until the run ends"
    )

    rep = sub.add_parser(
        "report", help="HTML report for one run, or a comparison of runs"
    )
    rep.add_argument("runs", nargs="+")
    rep.add_argument("--out")

    lift = sub.add_parser("lift", help="exact A_q <= q+m-2 lifting check (numpy)")
    lift.add_argument("m", type=int)
    lift.add_argument("r", type=int)
    lift.add_argument("--q", type=int, help="projection cap (default P=E_{r-1}(n-1))")
    lift.add_argument("--out", help="write the JSON report to this new file")

    args = parser.parse_args(argv)
    cmd = args.command
    if cmd == "lift":
        import sys as _sys

        from .lifting_fast import check_graph

        rep = check_graph(
            args.m,
            args.r,
            q=args.q,
            log=lambda s: print(s, file=_sys.stderr, flush=True),
        )
        rep.update(source="src/lrx/lifting_fast.py")
        if args.out:
            out = Path(args.out)
            if out.exists():
                raise FileExistsError(f"refusing to overwrite {out}")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rep, indent=1) + "\n")
        _print(rep)
        return 0 if rep["lifting_bound_holds_on_this_graph"] else 1
    if cmd == "trace":
        return _trace(args)
    if cmd == "report":
        from .report import write_report

        path, size = write_report(args.runs, args.out)
        _print({"report": path, "bytes": size})
        return 0
    if cmd == "table":
        return _table(args)
    if cmd == "eval":
        from .evaluator import evaluate
        from .feedback import compress

        result = evaluate(_load_json(args.candidate), split=args.split)
        if args.feedback:
            out = compress(result)
        elif args.full:
            out = result
        else:
            out = {
                k: result.get(k)
                for k in (
                    "candidate_hash",
                    "kind",
                    "valid",
                    "error",
                    "score",
                    "feasible",
                    "stopped",
                    "split",
                    "evaluator_sha256",
                    "seconds",
                )
            }
            out["graphs"] = [
                {
                    k: g.get(k)
                    for k in (
                        "graph",
                        "role",
                        "score",
                        "checked",
                        "failures",
                        "incomplete",
                        "value_max",
                        "T",
                        "excess_T",
                        "gap_mean",
                    )
                }
                for g in result.get("graphs", [])
            ]
        _print(out)
        return 0 if result.get("valid") else 2
    if cmd == "certify":
        from .evaluator import certify

        out = certify(_load_json(args.candidate), args.m, args.r)
        _print(out)
        return 0 if out["holds_on_graph"] else 1
    if cmd == "features":
        from .dsl import features

        _print(features(tuple(int(x) for x in args.v.split(",")), args.m, args.r))
        return 0
    if cmd == "evolve":
        from .evolve import run_campaign

        cfg = _load_json(args.config)
        for key in ("max_proposals", "engine", "seed"):
            if getattr(args, key) is not None:
                cfg[key] = getattr(args, key)
        out = run_campaign(cfg, args.run_dir, allow_network=args.allow_network)
        _print(
            {
                k: out[k]
                for k in (
                    "run_dir",
                    "engine",
                    "stop_reason",
                    "proposals",
                    "valid_proposals",
                    "seed_best",
                    "best",
                    "heldout",
                    "usage",
                    "wall_seconds",
                )
            }
        )
        return 0
    if cmd == "prompt":
        from . import prompt

        cfg = _load_json(args.config)
        kinds = cfg.get("kinds", ["rules"])
        seeds = cfg.get("seeds", [])
        parents = (
            [(_load_json(seeds[0]), {"note": "evaluator feedback goes here"})]
            if seeds
            else []
        )
        msgs = prompt.messages(prompt_task(), parents, kinds)
        _print(
            {
                "prefix_sha256": prompt.prefix_hash(kinds),
                "approx_tokens": sum(len(m["content"]) for m in msgs) // 4,
                "messages": msgs,
            }
        )
        return 0
    if cmd == "leaderboard":
        return _leaderboard(args.runs)
    if cmd == "llm-smoke":
        return _llm_smoke(args)
    return 2


def prompt_task():
    from .proposers import TASKS

    return TASKS["exploit"]


def _trace(args):
    from . import trace

    if args.follow:
        return _follow(Path(args.run) / "events.jsonl")
    run = trace.load_run(args.run)
    if args.tree:
        print("\n".join(trace.lineage_lines(run)))
    elif args.timeline:
        for row in trace.timeline_rows(run):
            _print(row)
    elif args.show is not None:
        c = trace.candidate_trace(run, args.show)
        c.pop("eval", None) if not c.get("eval_path") else None
        _print(c)
    else:
        _print(trace.overview(run))
    return 0


def _follow(path, poll=1.0, idle_limit=None):
    """Print one compact line per event as the run appends them."""
    import time

    pos, idle = 0, 0.0
    while True:
        if path.exists():
            with open(path) as fh:
                fh.seek(pos)
                for line in fh:
                    if not line.endswith("\n"):
                        break
                    pos += len(line)
                    event = json.loads(line)
                    print(_event_line(event), flush=True)
                    if event.get("event") == "end":
                        return 0
                    idle = 0.0
        time.sleep(poll)
        idle += poll
        if idle_limit is not None and idle >= idle_limit:
            return 2


def _event_line(e):
    kind = e.get("event")
    t = f"{e.get('t', 0):8.1f}s"
    if kind == "candidate":
        name = (e.get("spec") or {}).get("name", "")
        return (
            f"{t} cand #{e['id']:<4} {e.get('status', ''):9} score={e.get('score')} "
            f"mode={e.get('mode')} isl={e.get('island')} ${e.get('cost_usd') or 0:.4f} {name}"
        )
    if kind == "batch":
        usage = e.get("usage") or {}
        return (
            f"{t} batch {e['batch']:<3} proposals={e['proposals']} best={e.get('best_score')} "
            f"stall={e.get('since_improvement')} spend=${usage.get('estimated_usd', 0) or 0:.4f}"
        )
    if kind == "reflection":
        return f"{t} reflection: {(e.get('text') or e.get('error') or '')[:160]!r}"
    if kind == "heldout":
        return f"{t} heldout #{e.get('id')} feasible_all={e.get('feasible_all')}"
    return f"{t} {kind}"


def _print(obj):
    print(json.dumps(obj, sort_keys=True, default=str))


def _table(args):
    from . import evaluator
    from .table_bfs import build_table, write_table

    if args.action == "build":
        try:
            dist, meta = build_table(
                args.m, args.r, workers=args.workers, max_bytes=args.max_bytes
            )
        except MemoryError as exc:
            _print({"status": "INCOMPLETE", "reason": str(exc)})
            return 2
        if not meta["complete"]:
            _print({"status": "INCOMPLETE", **meta})
            return 2
        meta = write_table(args.out, args.m, args.r, dist, meta)
        _print(
            {
                "status": "COMPLETE",
                **{k: v for k, v in meta.items() if k != "layer_sizes"},
            }
        )
        return 0
    if args.action == "build-registry":
        report = evaluator.build_registry_tables(workers=args.workers)
        _print({"status": "COMPLETE", "tables": report})
        return 0
    # verify
    registry = evaluator.load_registry()
    rows, ok = [], True
    for g in registry["graphs"]:
        if not g.get("table"):
            continue
        try:
            table = evaluator.get_table(g["m"], g["r"])
            rows.append(
                {
                    "graph": f"m{g['m']}r{g['r']}",
                    "radius": table.radius,
                    "states": table.meta["states"],
                    "ok": True,
                }
            )
        except (OSError, ValueError) as exc:
            ok = False
            rows.append(
                {"graph": f"m{g['m']}r{g['r']}", "ok": False, "reason": str(exc)}
            )
    _print({"ok": ok, "tables": rows})
    return 0 if ok else 2


def _leaderboard(runs_dir):
    rows = []
    for path in sorted(Path(runs_dir).glob("*/summary.json")):
        try:
            s = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        best = s.get("best") if isinstance(s.get("best"), dict) else {}
        if s.get("engine") == "gepa-official":
            # Official GEPA summaries use their own schema.
            best = {
                "score": s.get("best_train_score"),
                "feasible_on_train_probes": s.get("best_feasible_train"),
            }
            s = dict(s, usage={"estimated_usd": s.get("usd")})
        rows.append(
            {
                "run": path.parent.name,
                "engine": s.get("engine"),
                "kinds": s.get("kinds"),
                "proposals": s.get("proposals"),
                "seed_best": s.get("seed_best"),
                "best_score": best.get("score"),
                "best_hash": best.get("hash"),
                "feasible_train": best.get("feasible_on_train_probes"),
                "heldout_feasible": [
                    h.get("feasible_all") for h in s.get("heldout", [])
                ][:1],
                "usd": (s.get("usage") or {}).get("estimated_usd"),
                "stop": s.get("stop_reason"),
            }
        )
    rows.sort(
        key=lambda r: -(r["best_score"] if r["best_score"] is not None else -1e18)
    )
    _print({"runs": rows})
    return 0


def _llm_smoke(args):
    from .evolve import build_proposer

    cfg = _load_json(args.config)
    proposer = build_proposer(cfg, args.allow_network)
    if not hasattr(proposer, "client"):
        _print({"status": "ERROR", "reason": "config provider is offline"})
        return 2
    seeds = cfg.get("seeds", [])
    parents = (
        [(_load_json(seeds[0]), {"note": "smoke test; no feedback"})] if seeds else []
    )
    out = proposer.propose("exploit", parents, cfg.get("kinds", ["rules"]), seed=1)
    result = None
    if out.get("spec") is not None:
        from .evaluator import evaluate

        result = evaluate(out["spec"], split="sanity")
    _print(
        {
            "error": out.get("error"),
            "parsed": out.get("spec") is not None,
            "valid": None if result is None else result.get("valid"),
            "sanity_score": None if result is None else result.get("score"),
            "tokens_in": out.get("tokens_in"),
            "tokens_out": out.get("tokens_out"),
            "reasoning_tokens": out.get("reasoning_tokens"),
            "finish_reason": out.get("finish_reason"),
            "seconds": out.get("seconds"),
            "cost_usd": out.get("cost_usd"),
            "cost_source": out.get("cost_source"),
            "usage": proposer.usage(),
            "reasoning_head": (out.get("reasoning") or "")[:800],
            "text_head": (out.get("text") or "")[:1500],
        }
    )
    return 0 if out.get("spec") is not None else 1
