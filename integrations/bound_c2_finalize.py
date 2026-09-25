"""Finalize bound-m campaign 2: per-(arm, seed) finalist by validation, holdout once, audit.

Human-run only, after the live runs (run-campaign-c2.sh calls it last).
1. For every live-<arm>-s<seed>-* run that is not FIRST_PROMPT_MISMATCH or INCOMPLETE, the
   accepted candidates are the seed, every source with a full development evaluation in the
   run's evaluation trace, the verified best, sequential's accepted steps and GEPA's candidate
   pool. Each is evaluated on the validation set (c1 holdout m = 11, sandboxed) and the finalist
   is the one with the most validation certificates, then the higher validation combined score,
   then the smaller source sha256. Development scores play no part in the choice.
2. Finalists and controls are frozen (finalists/manifest.json, sources copied). Then each is
   evaluated on development (for the generalization gap) and exactly once on the holdout
   (m = 12 and fresh m = 11), journaled per key as in bound_finalize.
   The run's development word pool (bound_c2.WordPool) is reported as a pooled certified count;
   it is not a uniform program and plays no part in selection.
3. Independent audit (bound_audit) of validation and holdout rows, determinism_check on the
   first 20 screen families, m-literal screen, and finalists/REPORT.md with per-arm n, mean, SD,
   min and max on validation and holdout and the gap (dev certified % minus holdout certified %).

`controls` evaluates the controls (naive, sweep-LP (b), campaign 1 GEPA finalist, seed) on
development and validation only; the holdout is left to finalize.

    python -m integrations.bound_c2_finalize controls --run-dir autoresearch/bound-m-c2-260925
    python -m integrations.bound_c2_finalize finalize --run-dir autoresearch/bound-m-c2-260925
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import time

from integrations.bound_finalize import ROW_KEYS, journaled, m_literals

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = ("FIRST_PROMPT_MISMATCH", "INCOMPLETE")
SUMMARY_KEYS = ("families", "certified", "boundary", "valid", "invalid", "incomplete", "timeouts", "max_W",
                "combined_score", "per_m", "candidate_hash", "isolation")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text())


def controls_of(cc):
    """name -> (kind, path or module). 'program' runs sandboxed; 'trusted' runs in-process (control b)."""
    c = cc["controls"]
    return {"naive": ("program", ROOT / c["naive"]), "sweeplp-b": ("trusted", "integrations.bound_control_sweeplp"),
            "gepa-c1": ("program", ROOT / c["gepa_c1"]), "seed-evox-c1": ("program", ROOT / c["seed_evox_c1"])}


def load_sets(camp):
    """(development, validation, holdout) family lists after hash checks against the c2 manifest."""
    from integrations import bound_evaluator as E

    man = _load(camp / "frozen" / "manifest.json")
    dev = ROOT / man["development"]["path"]
    if _sha(dev.read_bytes()) != man["development"]["sha256"]:
        raise SystemExit("abort: development hash differs from the c2 manifest")
    out = {"development": (dev, E.load_set(dev))}
    for name in ("validation", "holdout"):
        p = camp / "frozen" / f"{name}.json"
        if _sha(p.read_bytes()) != man["files"][f"{name}.json"]:
            raise SystemExit(f"abort: {name} hash differs from the c2 manifest")
        out[name] = (p, E.load_set(p, allow_holdout=True))
    return out


def summarize(res):
    return dict({k: res[k] for k in SUMMARY_KEYS if k in res}, tuple=_tuple(res),
                rows=[{k: r.get(k) for k in ROW_KEYS} for r in res["results"]])


def _tuple(res):
    from integrations.bound_evaluator import holdout_tuple
    return holdout_tuple(res)


def run_program(kind, target, fams, jobs, cache_dir=None):
    from integrations import bound_evaluator as E

    if kind == "trusted":
        return summarize(E.evaluate_trusted(target, fams, jobs=jobs))
    return summarize(E.evaluate(target, fams, require_os_sandbox=True, jobs=jobs, cache_dir=cache_dir))


# ------------------------------------------------------------------ selection
def accepted_candidates(run_dir, manifest) -> dict:
    """{sha256: source path} of every accepted candidate of one run (see module docstring)."""
    files = {}
    for p in sorted((Path(run_dir) / "verified" / "evaluations").glob("candidate-*.py")):
        files.setdefault(_sha(p.read_bytes()), p)
    best = Path(run_dir) / "verified" / "best.py"
    if best.is_file():
        files.setdefault(_sha(best.read_bytes()), best)
    want = {manifest.get("verified_best_hash")}
    want |= {r["candidate_hash"] for r in manifest.get("evaluation_trace", []) if r.get("full")}
    mech = manifest.get("mechanism_evidence") or {}
    want |= set(mech.get("candidate_sha256") or []) | set(mech.get("accepted_hashes") or [])
    want.add(manifest.get("seed_sha256"))
    return {h: files[h] for h in sorted(x for x in want if x) if h in files}


def selection_key(sha, val):
    """Validation-only ranking key (larger is better): certified, combined score, then smaller sha."""
    return (val["certified"], val["combined_score"], tuple(-ord(c) for c in sha))


def select_finalist(validation: dict) -> str:
    """The finalist sha among {sha: validation result}; uses validation results only."""
    if not validation:
        raise ValueError("no accepted candidates")
    return max(validation, key=lambda h: selection_key(h, validation[h]))


def stats(values) -> dict:
    v = [float(x) for x in values if x is not None]
    if not v:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {"n": len(v), "mean": statistics.fmean(v), "sd": statistics.stdev(v) if len(v) > 1 else None,
            "min": min(v), "max": max(v)}


def pct(res):
    return 100.0 * res["certified"] / res["families"]


# ------------------------------------------------------------------ commands
def controls(args):
    camp = args.run_dir.resolve()
    cc = _load(camp / "campaign-config.json")
    sets = load_sets(camp)
    out = camp / "controls"
    out.mkdir(exist_ok=True)
    table = {}
    for name, (kind, target) in controls_of(cc).items():
        for set_name in ("development", "validation"):
            path = out / f"{name}-{set_name}.json"
            if path.exists():
                res = _load(path)
            else:
                res = run_program(kind, target, sets[set_name][1], args.jobs, ROOT / cc["eval_cache"])
                res["file_sha256"] = _sha(sets[set_name][0].read_bytes())
                path.write_text(json.dumps(res) + "\n")
            table[f"{name}/{set_name}"] = {"certified": res["certified"], "families": res["families"],
                                           "incomplete": res["incomplete"], "max_W": res["max_W"],
                                           "combined": round(res["combined_score"], 4)}
    (out / "summary.json").write_text(json.dumps(table, indent=1) + "\n")
    return table


def finalize(args):
    from integrations import bound_audit
    from integrations import bound_evaluator as E

    camp = args.run_dir.resolve()
    cc = _load(camp / "campaign-config.json")
    sets = load_sets(camp)
    cache = ROOT / cc["eval_cache"]
    out = camp / "finalists"
    out.mkdir(exist_ok=True)
    runs = {}
    for d in sorted(p for p in camp.glob("live-*") if (p / "manifest.json").is_file()):
        m = _load(d / "manifest.json")
        if m.get("status") in EXCLUDED or not m.get("verified_best_hash"):
            continue
        runs[f"{m['engine']}-s{m['seed']}"] = (d, m)  # later stamp wins; fresh paths make this one run each
    # 1. validation selection (validation results journaled per candidate; cached by the evaluator)
    val_fams = sets["validation"][1]
    selection = {}
    for key, (d, m) in sorted(runs.items()):
        cands = accepted_candidates(d, m)
        val = {}
        for h, p in cands.items():
            res = E.evaluate(p, val_fams, require_os_sandbox=True, jobs=args.jobs, cache_dir=cache)
            val[h] = {"certified": res["certified"], "combined_score": res["combined_score"],
                      "incomplete": res["incomplete"], "families": res["families"]}
        best = select_finalist(val)
        selection[key] = {"run_dir": str(d), "engine": m["engine"], "seed": m["seed"], "status": m["status"],
                          "candidates": {h: str(p) for h, p in cands.items()}, "validation": val,
                          "finalist": best, "finalist_is_seed": best == m.get("seed_sha256"),
                          "word_pool_certified": (m.get("word_pool") or {}).get("certified")}
    (out / "selection.json").write_text(json.dumps(selection, indent=1) + "\n")
    # 2. freeze
    finalists = {k: Path(s["candidates"][s["finalist"]]) for k, s in selection.items()}
    ctl = controls_of(cc)
    frozen = {"frozen_sources": {k: _sha(p.read_bytes()) for k, p in finalists.items()},
              "controls": {k: (_sha(t.read_bytes()) if kind == "program" else t) for k, (kind, t) in ctl.items()},
              "files": {n: _sha(p.read_bytes()) for n, (p, _) in sets.items()},
              "evaluator": {"version": E.VERSION, "contract": E.CONTRACT, "hash": E.evaluator_hash()}}
    mpath = out / "manifest.json"
    (out / "sources").mkdir(exist_ok=True)
    if mpath.exists():
        if {k: _load(mpath).get(k) for k in frozen} != frozen:
            raise SystemExit("refusing: finalists/manifest.json is frozen with different hashes")
    else:
        for k, p in finalists.items():
            shutil.copyfile(p, out / "sources" / f"{k}.py")
        mpath.write_text(json.dumps(dict(frozen, created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                                    indent=1) + "\n")
    programs = {k: ("program", out / "sources" / f"{k}.py") for k in finalists}
    for k, (kind, t) in programs.items():
        if _sha(t.read_bytes()) != frozen["frozen_sources"][k]:
            raise SystemExit(f"abort: frozen source copy for {k} changed")
    programs.update(ctl)
    # 3. development, validation (controls and finalists), holdout once
    results = {}
    for name in ("development", "validation", "holdout"):
        path, fams = sets[name]
        file_sha, journal = _sha(path.read_bytes()), out / f"{name}-arms"
        results[name] = {k: journaled(journal, k, file_sha, name == "holdout",
                                      lambda kind=kind, t=t, fams=fams: run_program(
                                          kind, t, fams, args.jobs, None if name == "holdout" else cache))
                         for k, (kind, t) in programs.items()}
    audit = {n: {k: len(bound_audit.audit_result(sets[n][1], {"results": v["rows"]})["disagreements"])
                 for k, v in results[n].items()} for n in ("validation", "holdout")}
    screen_ids = _load(sets["development"][0])["screen"]
    screen = [f for f in sets["development"][1] if f["id"] in set(screen_ids)][:20]
    det, literals = {}, {}
    for k, (kind, t) in programs.items():
        if kind == "program":
            det[k] = E.determinism_check(t, screen, require_os_sandbox=True, jobs=args.jobs)
            literals[k] = m_literals(Path(t).read_text())
    summary = summary_table(selection, results, audit, det, literals)
    (out / "results.json").write_text(json.dumps({"summary": summary, "audit": audit, "determinism": det,
                                                  "m_literals": literals}, indent=1) + "\n")
    (out / "REPORT.md").write_text(report(summary))
    return {"per_arm": summary["per_arm"], "audit_disagreements": audit,
            "nondeterministic": [k for k, v in det.items() if not v["deterministic"]]}


def summary_table(selection, results, audit, det, literals):
    rows = {}
    for k in results["holdout"]:
        dv, va, ho = results["development"][k], results["validation"][k], results["holdout"][k]
        rows[k] = {"dev_pct": pct(dv), "validation_pct": pct(va), "holdout_pct": pct(ho),
                   "holdout_per_m": {m: [x["certified"], x["families"]] for m, x in ho["per_m"].items()},
                   "gap": pct(dv) - pct(ho), "holdout_incomplete": ho["incomplete"],
                   "audit_disagreements": audit["validation"][k] + audit["holdout"][k],
                   "deterministic": det[k]["deterministic"] if k in det else None,
                   "m_literals": len(literals.get(k, [])),
                   "finalist_is_seed": selection.get(k, {}).get("finalist_is_seed"),
                   "run_pool_certified_dev": selection.get(k, {}).get("word_pool_certified"),
                   "candidates": len(selection.get(k, {}).get("candidates", {}))}
    per_arm = {}
    for arm in ("gepa", "sequential", "adaevolve", "evox"):
        keys = [k for k in selection if selection[k]["engine"] == arm]
        per_arm[arm] = {x: stats(rows[k][x] for k in keys) for x in ("validation_pct", "holdout_pct", "gap")}
    return {"rows": rows, "per_arm": per_arm}


def _fmt(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def report(summary):
    lines = ["# bound-m-c2-260925 finalists", "",
             "Every CERTIFIED family (a,S) is a machine-checked bound d(v) <= T_m(n) for all its block lengths, "
             "conditional on the group's Lemma 1 and criterion (7) with m as a parameter. A miss, crash or timeout "
             "proves nothing. Finalists were chosen by validation (c1 holdout m=11) only; the holdout (m=12 and fresh "
             "m=11) was evaluated once after freeze. Gap = development certified % minus holdout certified %.", "",
             "## Per arm (one finalist per seed)", "",
             "| arm | n | validation % mean (SD) [min, max] | holdout % mean (SD) [min, max] | gap mean (SD) |",
             "|---|---|---|---|---|"]
    for arm, s in summary["per_arm"].items():
        v, h, g = s["validation_pct"], s["holdout_pct"], s["gap"]
        lines.append(f"| {arm} | {v['n']} | {_fmt(v['mean'])} ({_fmt(v['sd'])}) [{_fmt(v['min'])}, {_fmt(v['max'])}] | "
                     f"{_fmt(h['mean'])} ({_fmt(h['sd'])}) [{_fmt(h['min'])}, {_fmt(h['max'])}] | "
                     f"{_fmt(g['mean'])} ({_fmt(g['sd'])}) |")
    lines += ["", "## Per finalist and control", "",
              "| key | candidates | validation % | dev % | holdout % | holdout C/N per m | gap | incomplete | "
              "audit disagreements | deterministic | m-literals | finalist is seed | run pool dev certified |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in summary["rows"].items():
        pm = " ".join(f"m{m}:{c}/{n}" for m, (c, n) in r["holdout_per_m"].items())
        lines.append(f"| {k} | {r['candidates']} | {_fmt(r['validation_pct'])} | {_fmt(r['dev_pct'])} | "
                     f"{_fmt(r['holdout_pct'])} | {pm} | {_fmt(r['gap'])} | {r['holdout_incomplete']} | "
                     f"{r['audit_disagreements']} | {r['deterministic']} | {r['m_literals']} | "
                     f"{r['finalist_is_seed']} | {r['run_pool_certified_dev'] if r['run_pool_certified_dev'] is not None else '-'} |")
    lines += ["", "An arm claims progress only if its mean holdout certified % over seeds beats both control (b) "
              "(sweeplp-b) and the seed (seed-evox-c1); single-seed wins are reported, not claimed.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("controls", "finalize"))
    ap.add_argument("--run-dir", type=Path, default=ROOT / "autoresearch" / "bound-m-c2-260925")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args(argv)
    print(json.dumps(controls(args) if args.action == "controls" else finalize(args), default=str))


if __name__ == "__main__":
    main()
