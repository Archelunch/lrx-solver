"""Finalize Track 3 arms: independent re-audit, `leanchecker --fresh`, and the pre-registered rules.

For every live arm directory (live-<engine>-*) with a manifest, the verified best
body is re-evaluated without any cache, its compiled subset is replayed with
`leanchecker --fresh` (every constant, imported ones included, into a fresh
environment), and closed targets are compared with the tactic-sweep control.
Success needs a target the control did not close, confirmed here, plus the
comparator judge (not installed on macOS: it needs Linux landrun) and a human
read of the proof text before anything enters research/claims.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from integrations import lean_evaluator as E
from integrations import lean_task as T
from integrations import lean_worker as W


def fresh_replay(body: str, wall: float = 600.0) -> dict:
    """Compile the body (stage A, sandboxed) and replay it with `leanchecker --fresh` (sandboxed)."""
    tc, build = T.toolchain_dir(), T.PROJECT / ".lake" / "build" / "lib" / "lean"
    with tempfile.TemporaryDirectory(prefix="lrx-lean-final-") as scratch:
        scratch = Path(os.path.realpath(scratch))
        (scratch / "a").mkdir()
        (scratch / "b").mkdir()
        run, parsed, _ = E._stage_a(body, scratch / "a", dict(E.DEFAULTS), True)
        errors = [m for m in parsed["messages"] if m["severity"] == "error"]
        if run["status"] != "ok" or run["returncode"] != 0 or errors:
            return {"status": "NOT_COMPILED", "stage_a": run["status"], "errors": len(errors)}
        execs = [tc / "bin" / "leanchecker", tc / "bin" / "lean"]
        profile = W.lean_profile(exec_paths=execs, read_paths=[tc, build, scratch / "a"],
                                 write_paths=[scratch / "b"], allow_fork=True)
        rb = W.run([execs[0], "--fresh", "Cand"], cwd=scratch / "b", env=E._env(scratch / "b", [build, scratch / "a"]),
                   profile_text=profile, wall=wall, rss_limit_mb=8192)
        return {"status": "PASS" if rb["status"] == "ok" and rb["returncode"] == 0 else
                ("INCOMPLETE" if rb["status"] != "ok" else "FAIL"),
                "returncode": rb["returncode"], "seconds": rb["seconds"], "stderr": E._sanitize(rb["stderr"])[:400]}


def finalize(track_dir: Path, control_path: Path, pattern: str = "live-*") -> dict:
    control = json.loads(control_path.read_text())
    floor = set(control["closed_targets"])
    arms = []
    for manifest_path in sorted(track_dir.glob(f"{pattern}/manifest.json")):
        m = json.loads(manifest_path.read_text())
        best = next((p for p in (manifest_path.parent / "verified").glob("best.*")), None)
        row = {"run_dir": str(manifest_path.parent.relative_to(T.ROOT)), "engine": m.get("engine"),
               "status": m.get("status"), "research_status": m.get("research_status")}
        if best is None or m.get("status") not in ("COMPLETE", "EVAL_BUDGET", "GUARD_STOPPED", "BROKER_STOPPED"):
            row["verdict"] = "EXCLUDED (no verified best or arm not complete)"
            arms.append(row)
            continue
        source = best.read_text()
        res = E.evaluate(source, cache_dir=None)
        row.update(best_sha256=hashlib.sha256(source.encode()).hexdigest(), reaudit_status=res["status"],
                   reaudit_score=res["combined_score"], closed_targets=res.get("closed_targets", []),
                   closed_milestones=res.get("closed_milestones", []),
                   matches_manifest=res.get("closed_targets") == (m.get("verified_best_result") or {}).get(
                       "closed_targets"))
        new = sorted(set(row["closed_targets"]) - floor)
        if new and res.get("verified_body"):
            row["fresh_replay"] = fresh_replay(res["verified_body"])
            row["verified_body_sha256"] = hashlib.sha256(res["verified_body"].encode()).hexdigest()
        confirmed = bool(new) and row.get("fresh_replay", {}).get("status") == "PASS"
        row["new_targets_vs_control"] = new
        row["verdict"] = ("CANDIDATE_SUCCESS: pending comparator and human read" if confirmed
                          else "NO_TARGET_BEYOND_CONTROL" if not new else "NOT_CONFIRMED")
        arms.append(row)
    return {"task": "lean-loop-260925", "evaluator_version": E.VERSION, "lock_digest": T.verify_lock(),
            "toolchain": E.check_toolchain(), "control": str(control_path.relative_to(T.ROOT)),
            "control_closed_targets": sorted(floor), "arms": arms,
            "comparator": "not run: leanprover/comparator needs Linux landrun; the Seatbelt shim is not built",
            "human_read": "required before any claim"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--track-dir", type=Path, default=T.TRACK_DIR)
    parser.add_argument("--control", type=Path, default=T.TRACK_DIR / "controls" / "sweep.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pattern", default="live-*", help="arm directories (smoke-* for mock smokes only)")
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit(f"{args.output} exists; use a fresh path")
    out = finalize(args.track_dir.resolve(), args.control.resolve(), args.pattern)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"arms": [(a["run_dir"], a["verdict"]) for a in out["arms"]]}))


if __name__ == "__main__":
    main()
