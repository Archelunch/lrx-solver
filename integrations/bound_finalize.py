"""Post-campaign finalize for bound-m: freeze finalists, evaluate the holdout once,
audit independently, compare with control (b), write finalists/REPORT.md.

Human-run only, after the live arms finish. Finalists are the verified best source
of each COMPLETE live-* arm plus controls (a) naive and (b16) sweep-16; control (b)
(sweep-LP, trusted in-process) is the reference an engine must beat on the holdout.
The holdout (m = 9, 10, 11) is loaded only here, after a hash check against
frozen/manifest.json, and each finalist is evaluated on it exactly once (the
result file is reused on later calls). Each arm's result is journaled to
finalists/<set>-arms/<arm>.json as soon as it is evaluated, after a <arm>.started
marker; a rerun reuses journaled arms and refuses to re-evaluate a holdout arm whose
marker has no result (an interrupted holdout run needs a human decision). Generated
finalists run only in the
Seatbelt sandbox. Also reports per-m results, determinism (two screen runs) and
m-literals in each finalist source (uniformity is only screened, SPEC 8).

    python -m integrations.bound_finalize --run-dir autoresearch/bound-m-260925
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = {"naive-control": ROOT / "integrations" / "bound_control_naive.py",
            "sweep16-control": ROOT / "integrations" / "bound_control_sweep.py"}
ROW_KEYS = ("id", "m", "k", "class", "status", "valid", "gap", "bound", "certificate", "output_words", "timeout")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def m_literals(source):
    """Lines comparing m (or len/max of the vector) with an integer literal: `if m == 9:`-style branches."""
    pat = re.compile(r"\b(m|n|k|len\([^)]*\)|max\([^)]*\))\s*(==|!=|<=|>=|<|>)\s*(9|10|11|12)\b")
    return [ln.strip() for ln in source.splitlines() if pat.search(ln)][:20]


def journaled(journal, arm, file_sha, once, run):
    """Arm result from journal/<arm>.json, else run() and record it at once.

    With `once` (the holdout), a <arm>.started marker without a result means an earlier
    evaluation began and never finished; the arm is not evaluated again."""
    done, started = journal / f"{arm}.json", journal / f"{arm}.started"
    if done.is_file():
        rec = json.loads(done.read_text())
        if rec.get("file_sha256") != file_sha:
            raise SystemExit(f"abort: journaled {arm} was evaluated on a different set file")
        return rec["result"]
    if once and started.exists():
        raise SystemExit(f"refusing: {started} shows an unfinished one-time evaluation of {arm}; not rerunning it")
    journal.mkdir(parents=True, exist_ok=True)
    started.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + "\n")
    result = run()
    tmp = done.with_suffix(".tmp")
    tmp.write_text(json.dumps({"arm": arm, "file_sha256": file_sha, "result": result}) + "\n")
    tmp.replace(done)
    return result


def finalize(args):
    from integrations import bound_audit
    from integrations import bound_evaluator as E
    from integrations.lift_backends import development_from_manifest

    camp = args.run_dir.resolve()
    out = camp / "finalists"
    fm = camp / "frozen" / "manifest.json"
    frozen = json.loads(fm.read_text())
    holdout = fm.parent / "holdout.json"
    if _sha(holdout.read_bytes()) != frozen["files"]["holdout.json"]:
        raise SystemExit("abort: holdout hash differs from the frozen manifest")
    development, dev_sha = development_from_manifest(fm)
    runs = {}
    for d in sorted(p for p in camp.glob("live-*") if (p / "manifest.json").is_file()):
        m = json.loads((d / "manifest.json").read_text())
        if m.get("status") != "COMPLETE" or not m.get("verified_best_full"):
            continue
        src = d / "verified" / "best.py"
        if not src.is_file():
            src = next(iter(sorted((d / "verified").glob("*.py"))), None)
        if src is None or _sha(src.read_bytes()) != m["verified_best_hash"]:
            raise SystemExit(f"abort: verified best of {d} does not match its manifest hash")
        key = (m["verified_best_full"]["certified"], m["verified_best_full"]["combined_score"])
        if m["engine"] not in runs or key > runs[m["engine"]][0]:
            runs[m["engine"]] = (key, d, m, src)
    finalists = [{"arm": e, "run_dir": str(d), "source": str(src), "source_sha256": m["verified_best_hash"],
                  "development_claim": m["verified_best_full"]} for e, (_, d, m, src) in sorted(runs.items())]
    finalists += [{"arm": a, "run_dir": None, "source": str(p), "source_sha256": _sha(p.read_bytes()),
                   "development_claim": None} for a, p in CONTROLS.items()]
    frozen_set = {"frozen_sources": {f["arm"]: f["source_sha256"] for f in finalists},
                  "holdout_sha256": frozen["files"]["holdout.json"], "development_sha256": dev_sha,
                  "frozen_manifest_sha256": _sha(fm.read_bytes()),
                  "evaluator": {"version": E.VERSION, "contract": E.CONTRACT, "hash": E.evaluator_hash()}}
    (out / "sources").mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    if mpath.exists():
        old = json.loads(mpath.read_text())
        if {k: old.get(k) for k in frozen_set} != frozen_set:
            raise SystemExit("refusing: finalists/manifest.json is frozen with different hashes")
    else:
        for f in finalists:
            shutil.copyfile(f["source"], out / "sources" / f"{f['arm']}.py")
        mpath.write_text(json.dumps(dict(frozen_set, created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                         details=finalists), indent=2, default=str) + "\n")
    srcs = {f["arm"]: out / "sources" / f"{f['arm']}.py" for f in finalists}
    for f in finalists:
        if _sha(srcs[f["arm"]].read_bytes()) != f["source_sha256"]:
            raise SystemExit(f"abort: frozen source copy for {f['arm']} changed")
    sets = {"holdout": (holdout, E.load_set(holdout, allow_holdout=True)),
            "development": (development, E.load_set(development))}
    results = {}
    for name, (path, fams) in sets.items():
        target = out / f"{name}-results.json"
        if target.exists():  # the holdout is evaluated exactly once; later calls reuse it
            results[name] = json.loads(target.read_text())
            if results[name]["file_sha256"] != _sha(path.read_bytes()):
                raise SystemExit(f"abort: {name} changed since its recorded evaluation")
            continue
        per_arm, file_sha, journal = {}, _sha(path.read_bytes()), out / f"{name}-arms"

        def run_arm(f, fams=fams):
            generated = f["arm"] not in CONTROLS
            res = E.evaluate(srcs[f["arm"]], fams, require_os_sandbox=generated or not args.no_os_sandbox,
                             jobs=args.jobs)
            return dict({k: res[k] for k in ("families", "certified", "boundary", "valid", "invalid",
                                             "incomplete", "timeouts", "max_W", "combined_score",
                                             "per_m", "seconds", "candidate_hash", "isolation")},
                        tuple=E.holdout_tuple(res), rows=[{k: r.get(k) for k in ROW_KEYS} for r in res["results"]])

        def run_ref(fams=fams):
            ref = E.evaluate_trusted("integrations.bound_control_sweeplp", fams, jobs=args.jobs)
            return dict({k: ref[k] for k in ("families", "certified", "boundary", "valid",
                                             "max_W", "combined_score", "per_m", "isolation")},
                        tuple=E.holdout_tuple(ref), rows=[{k: r.get(k) for k in ROW_KEYS} for r in ref["results"]])

        for f in finalists:
            per_arm[f["arm"]] = journaled(journal, f["arm"], file_sha, name == "holdout", lambda f=f: run_arm(f))
        per_arm["sweeplp-control-b"] = journaled(journal, "sweeplp-control-b", file_sha, name == "holdout", run_ref)
        results[name] = {"set": name, "file_sha256": _sha(path.read_bytes()),
                         "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "evaluated_once": name == "holdout", "arms": per_arm}
        target.write_text(json.dumps(results[name]) + "\n")
    audit = {}
    for name, (_, fams) in sets.items():
        audit[name] = {a: bound_audit.audit_result(fams, {"results": v["rows"]}) for a, v in results[name]["arms"].items()}
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    screen_ids = set(json.loads(development.read_text())["screen"])
    screen = [f for f in sets["development"][1] if f["id"] in screen_ids]
    determinism, literals = {}, {}
    for f in finalists:
        runs2 = [E.evaluate(srcs[f["arm"]], screen, require_os_sandbox=True, jobs=args.jobs) for _ in range(2)]
        determinism[f["arm"]] = [r.get("output_words") for r in runs2[0]["results"]] == \
                                [r.get("output_words") for r in runs2[1]["results"]]
        literals[f["arm"]] = m_literals(srcs[f["arm"]].read_text())
    (out / "REPORT.md").write_text(report(results, audit, determinism, literals))
    return {"holdout_certified": {a: v["certified"] for a, v in results["holdout"]["arms"].items()},
            "audit_disagreements": {n: {a: len(v["disagreements"]) for a, v in d.items()} for n, d in audit.items()}}


def report(results, audit, determinism, literals):
    ref = results["holdout"]["arms"]["sweeplp-control-b"]["certified"]
    lines = ["# bound-m-260925 finalists", "",
             "Every CERTIFIED family (a,S) is a machine-checked bound d(v) <= T_m(n) for all its block lengths, "
             "conditional on the group's Lemma 1 and criterion (7) with m as a parameter. It says nothing about "
             "other families. A miss, crash or timeout proves nothing.", "",
             "| arm | holdout certified (m=9/10/11) | holdout W (m=9/10/11) | dev certified (m=9/10) | beats (b) | "
             "audit disagreements | deterministic | m-literals |", "|---|---|---|---|---|---|---|---|"]
    for arm, h in results["holdout"]["arms"].items():
        dv = results["development"]["arms"][arm]
        cm = "/".join(str(h["per_m"][m]["certified"]) for m in sorted(h["per_m"], key=int))
        wm = "/".join(h["per_m"][m]["W"] for m in sorted(h["per_m"], key=int))
        dm = "/".join(str(dv["per_m"][m]["certified"]) for m in sorted(dv["per_m"], key=int))
        dis = sum(len(audit[n][arm]["disagreements"]) for n in audit)
        lines.append(f"| {arm} | {cm} | {wm} | {dm} | {'yes' if h['certified'] > ref else 'no'} | {dis} | "
                     f"{determinism.get(arm, '-')} | {len(literals.get(arm, []))} |")
    lines += ["", "An engine claims progress only if it beats control (b) on the holdout (strictly more certified).", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", type=Path, default=ROOT / "autoresearch" / "bound-m-260925")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-os-sandbox", action="store_true", help="trusted controls only; generated code always sandboxed")
    print(json.dumps(finalize(ap.parse_args(argv))))


if __name__ == "__main__":
    main()
