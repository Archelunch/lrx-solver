"""Finalize bound-m campaign 3: per-(arm, seed) finalist by validation, holdout once, audit.

Human-run only, after the live runs (run-campaign-c3.sh calls it last). Mirrors
bound_c2_finalize.py but scores with the tree contract (bound3_evaluator, bound-eval-3) and
carries campaign 3's specifics from TASK-c3.md:

1. For every live-<arm>-s<seed>-* run that is not FIRST_PROMPT_MISMATCH or INCOMPLETE, the
   accepted candidates are the seed, every source with a full development evaluation in the
   run's evaluation trace, the verified best and GEPA's candidate pool (bound_c2_finalize's
   accepted_candidates/select_finalist; the manifest schema is bound_backends._finish's, shared
   by campaigns 2 and 3). Each is evaluated on the validation set (c2 validation.json, m = 11,
   sandboxed) and the finalist is the one with the most validation certificates, then the higher
   validation combined score, then the smaller source sha256. Development scores play no part.
2. Finalists and controls (seed-c3, adaevolve-s2-one-leaf, revtree-b) are frozen
   (finalists/manifest.json, sources copied for the finalists; controls run from their own
   paths). revtree-b is a trusted, table-fed, non-uniform reference: it is evaluated on
   development only, never at m = 11 or 12 (TASK-c3.md). Each program is evaluated on
   development (generalization gap), validation and, exactly once, the holdout (c2
   holdout.json: 165 m = 12 + 60 fresh m = 11); results are journaled per key as in
   bound_finalize, and a holdout journal entry is never re-run.
3. Independent audit (bound3_audit) of validation and holdout CERTIFIED claims, a determinism
   check (two sandboxed bound-eval-3 runs on the first 20 screen families, raw tree outputs
   compared per family), an m-literal source screen, per-class certified counts on the m = 12
   holdout (including the seed and control rows), the 14 pre-registered target families
   (recomputed from the stored campaign-2 holdout rows; finalize aborts unless there are exactly
   14), the pre-registered per-arm success rule and finalists/REPORT.md.

    python -m integrations.bound_c3_finalize finalize --run-dir autoresearch/bound-m-c3-260926
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import time

from integrations import bound_c2_finalize as c2fin
from integrations import bound_c2 as c2
from integrations.bound_finalize import journaled, m_literals

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = ("FIRST_PROMPT_MISMATCH", "INCOMPLETE")
SUMMARY_KEYS = ("families", "certified", "boundary", "valid", "invalid", "incomplete", "timeouts", "max_W",
                "combined_score", "per_m", "candidate_hash", "isolation")
ROW_KEYS = ("id", "m", "k", "class", "status", "valid", "gap", "bound", "certificate", "output", "n_leaves",
            "timeout")
# TASK-c3.md success rule 2: the m=12 holdout families none of AdaEvolve-s2, EvoX-s3, the c2 seed
# and control (b) certify, from the campaign-2 stored holdout rows.
C2_CAMP = ROOT / "autoresearch" / "bound-m-c2-260925"
TARGET_ARMS = ("adaevolve-s2", "evox-s3", "seed-evox-c1", "sweeplp-b")
TARGET_COUNT = 14
NON_UNIFORM_CONTROLS = ("revtree-b",)  # never evaluated on validation/holdout (m=11,12): table-fed, m<=10 only


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text())


def controls_of(cc):
    """name -> (kind, path or module). 'program' runs sandboxed; 'trusted' runs in-process."""
    c = cc["controls"]
    return {"seed-c3": ("program", ROOT / c["seed_c3"]),
            "adaevolve-s2-one-leaf": ("program", ROOT / c["adaevolve_s2_one_leaf"]),
            "revtree-b": ("trusted", "integrations.bound3_control_revtree")}


def load_sets(camp, cc):
    """(development, validation, holdout) family lists after hash checks against the c2 manifest."""
    from integrations import bound_evaluator as E

    dev, _c1_man, man_path = c2.frozen_paths(cc)
    man = _load(man_path)
    out = {"development": (dev, E.load_set(dev))}
    for name in ("validation", "holdout"):
        p = man_path.parent / f"{name}.json"
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
    from integrations import bound3_evaluator as B3

    if kind == "trusted":
        return summarize(B3.evaluate_trusted(target, fams, jobs=jobs))
    return summarize(B3.evaluate(target, fams, require_os_sandbox=True, jobs=jobs, cache_dir=cache_dir))


def determinism_check(target, screen, jobs):
    """Two sandboxed bound-eval-3 runs; raw tree ("output") outputs compared per family (TASK-c3.md)."""
    from integrations import bound3_evaluator as B3

    runs = [B3.evaluate(target, screen, require_os_sandbox=True, jobs=jobs) for _ in range(2)]
    first = {r["id"]: r.get("output") for r in runs[0]["results"]}
    second = {r["id"]: r.get("output") for r in runs[1]["results"]}
    mismatches = sorted(fid for fid in first if first[fid] != second.get(fid))
    return {"deterministic": not mismatches, "mismatches": mismatches}


# ------------------------------------------------------------------ target families
def target_m12_families(c2_camp=C2_CAMP, arms=TARGET_ARMS) -> list:
    """The pre-registered 14 m=12 holdout families none of `arms` certify, recomputed from the
    stored campaign-2 finalists/holdout-arms/<arm>.json rows (TASK-c3.md finalize success rule)."""
    ids, m12 = None, None
    for arm in arms:
        rec = _load(Path(c2_camp) / "finalists" / "holdout-arms" / f"{arm}.json")
        rows = rec["result"]["rows"]
        if m12 is None:
            m12 = {r["id"] for r in rows if r["m"] == 12}
        certified = {r["id"] for r in rows if r["status"] == "CERTIFIED"}
        missed = m12 - certified
        ids = missed if ids is None else (ids & missed)
    return sorted(ids)


# ------------------------------------------------------------------ selection
def selection_key(sha, val):
    return c2fin.selection_key(sha, val)


def select_finalist(validation: dict) -> str:
    return c2fin.select_finalist(validation)


def stats(values) -> dict:
    return c2fin.stats(values)


def pct(res):
    return 100.0 * res["certified"] / res["families"]


def m_pct(res, m):
    g = res["per_m"].get(str(m))
    return None if g is None else 100.0 * g["certified"] / g["families"]


def per_class(rows, m):
    c = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["m"] != m:
            continue
        c[r["class"]][1] += 1
        c[r["class"]][0] += r["status"] == "CERTIFIED"
    return {k: v for k, v in sorted(c.items())}


def target_certified(rows, target_ids) -> int:
    target = set(target_ids)
    return sum(1 for r in rows if r["id"] in target and r["status"] == "CERTIFIED")


# ------------------------------------------------------------------ command
def finalize(args):
    from integrations import bound3_audit
    from integrations import bound3_evaluator as B3

    camp = args.run_dir.resolve()
    cc = _load(camp / "campaign-config-c3.json")
    sets = load_sets(camp, cc)
    cache = ROOT / cc["eval_cache"]
    out = camp / "finalists"
    out.mkdir(exist_ok=True)
    target_ids = target_m12_families()
    if len(target_ids) != TARGET_COUNT:
        raise SystemExit(f"abort: expected {TARGET_COUNT} target m=12 families, recomputed {len(target_ids)}")
    runs = {}
    for d in sorted(p for p in camp.glob("live-*") if (p / "manifest.json").is_file()):
        m = _load(d / "manifest.json")
        if m.get("status") in EXCLUDED or not m.get("verified_best_hash"):
            continue
        runs[f"{m['engine']}-s{m['seed']}"] = (d, m)
    # 1. validation selection (validation certificates, journaled/cached by the evaluator)
    val_fams = sets["validation"][1]
    selection = {}
    for key, (d, m) in sorted(runs.items()):
        cands = c2fin.accepted_candidates(d, m)
        val = {}
        for h, p in cands.items():
            res = B3.evaluate(p, val_fams, require_os_sandbox=True, jobs=args.jobs, cache_dir=cache)
            val[h] = {"certified": res["certified"], "combined_score": res["combined_score"],
                      "incomplete": res["incomplete"], "families": res["families"]}
        best = select_finalist(val)
        selection[key] = {"run_dir": str(d), "engine": m["engine"], "seed": m["seed"], "status": m["status"],
                          "candidates": {h: str(p) for h, p in cands.items()}, "validation": val,
                          "finalist": best, "finalist_is_seed": best == m.get("seed_sha256")}
    (out / "selection.json").write_text(json.dumps(selection, indent=1) + "\n")
    # 2. freeze
    finalists = {k: Path(s["candidates"][s["finalist"]]) for k, s in selection.items()}
    ctl = controls_of(cc)
    frozen = {"frozen_sources": {k: _sha(p.read_bytes()) for k, p in finalists.items()},
              "controls": {k: (_sha(t.read_bytes()) if kind == "program" else t) for k, (kind, t) in ctl.items()},
              "files": {n: _sha(p.read_bytes()) for n, (p, _) in sets.items()}, "target_families": target_ids,
              "evaluator": {"version": B3.VERSION, "contract": B3.CONTRACT, "hash": B3.evaluator_hash()}}
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
    # 3. development, validation, holdout once; revtree-b (table-fed, non-uniform) skips validation/holdout
    results = {}
    for name in ("development", "validation", "holdout"):
        path, fams = sets[name]
        file_sha, journal = _sha(path.read_bytes()), out / f"{name}-arms"
        keys = programs if name == "development" else {k: v for k, v in programs.items()
                                                        if k not in NON_UNIFORM_CONTROLS}
        results[name] = {k: journaled(journal, k, file_sha, name == "holdout",
                                      lambda kind=kind, t=t, fams=fams: run_program(
                                          kind, t, fams, args.jobs, None if name == "holdout" else cache))
                         for k, (kind, t) in keys.items()}
    audit = {n: {k: len(bound3_audit.audit_result(sets[n][1], {"results": v["rows"]})["disagreements"])
                 for k, v in results[n].items()} for n in ("validation", "holdout")}
    screen_ids = _load(sets["development"][0])["screen"]
    screen = [f for f in sets["development"][1] if f["id"] in set(screen_ids)][:20]
    det, literals = {}, {}
    for k, (kind, t) in programs.items():
        if kind == "program":
            det[k] = determinism_check(t, screen, args.jobs)
            literals[k] = m_literals(Path(t).read_text())
    summary = summary_table(selection, results, audit, det, literals, target_ids)
    (out / "results.json").write_text(json.dumps({"summary": summary, "audit": audit, "determinism": det,
                                                  "m_literals": literals, "target_families": target_ids},
                                                 indent=1) + "\n")
    (out / "REPORT.md").write_text(report(summary, target_ids))
    return {"per_arm": summary["per_arm"], "success": summary["success"], "audit_disagreements": audit,
            "nondeterministic": [k for k, v in det.items() if not v["deterministic"]]}


def summary_table(selection, results, audit, det, literals, target_ids):
    rows = {}
    for k in results["holdout"]:
        dv, ho = results["development"][k], results["holdout"][k]
        va = results["validation"].get(k)
        rows[k] = {"dev_pct": pct(dv), "validation_pct": pct(va) if va else None,
                   "holdout_m12_pct": m_pct(ho, 12), "holdout_m11_pct": m_pct(ho, 11),
                   "per_class_m12": per_class(ho["rows"], 12), "target_certified": target_certified(
                       ho["rows"], target_ids), "gap": pct(dv) - (m_pct(ho, 12) or 0.0),
                   "holdout_incomplete": ho["incomplete"],
                   "audit_disagreements": (audit["validation"].get(k, 0) + audit["holdout"].get(k, 0)),
                   "deterministic": det[k]["deterministic"] if k in det else None,
                   "m_literals": len(literals.get(k, [])),
                   "finalist_is_seed": selection.get(k, {}).get("finalist_is_seed"),
                   "candidates": len(selection.get(k, {}).get("candidates", {}))}
    seed_m12 = rows.get("seed-c3", {}).get("holdout_m12_pct")
    per_arm = {}
    for arm in ("gepa", "sequential", "adaevolve", "evox"):
        keys = [k for k in selection if selection[k]["engine"] == arm]
        m12 = stats(rows[k]["holdout_m12_pct"] for k in keys)
        tgt = stats(rows[k]["target_certified"] for k in keys)
        gap = stats(rows[k]["gap"] for k in keys)
        cond1 = seed_m12 is not None and m12["mean"] is not None and m12["mean"] >= seed_m12 + 3.0
        cond2 = tgt["mean"] is not None and tgt["mean"] >= 5.0
        per_arm[arm] = {"holdout_m12_pct": m12, "target_certified": tgt, "gap": gap,
                        "condition_1_beats_seed_plus_3pp": bool(cond1),
                        "condition_2_target_mean_ge_5": bool(cond2), "success": bool(cond1 and cond2)}
    success = {arm: s["success"] for arm, s in per_arm.items()}
    return {"rows": rows, "per_arm": per_arm, "seed_c3_holdout_m12_pct": seed_m12, "success": success}


def _fmt(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def report(summary, target_ids):
    lines = ["# bound-m-c3-260926 finalists", "",
             "Every CERTIFIED family (a,S) is a machine-checked bound d(v) <= T_m(n) for all its block lengths, "
             "conditional on the group's Lemma 1 with refinement and criterion (8) with m as a parameter. A miss, "
             "crash or timeout proves nothing. Finalists were chosen by validation (c2 validation.json, m=11) "
             "only; the holdout (c2 holdout.json: 165 m=12, 60 fresh m=11) was evaluated once after freeze. "
             "revtree-b is a trusted, table-fed, non-uniform reference and is never evaluated at m=11 or 12. "
             f"gap = development certified % minus holdout m=12 certified %. Target families ({len(target_ids)}): "
             "the m=12 holdout families none of AdaEvolve-s2, EvoX-s3, the c2 seed and control (b) certify "
             "(BEST-C2-CONSTRUCTION.md section 2).", "",
             "## Pre-registered success rule per arm", "",
             "| arm | n | holdout m=12 % mean (SD) [min, max] | vs seed+3pp | target certified mean (SD) [min, max] "
             "| target >= 5 | success |", "|---|---|---|---|---|---|---|"]
    for arm, s in summary["per_arm"].items():
        m12, tgt = s["holdout_m12_pct"], s["target_certified"]
        lines.append(f"| {arm} | {m12['n']} | {_fmt(m12['mean'])} ({_fmt(m12['sd'])}) [{_fmt(m12['min'])}, "
                     f"{_fmt(m12['max'])}] | {s['condition_1_beats_seed_plus_3pp']} | {_fmt(tgt['mean'])} "
                     f"({_fmt(tgt['sd'])}) [{_fmt(tgt['min'])}, {_fmt(tgt['max'])}] | "
                     f"{s['condition_2_target_mean_ge_5']} | {s['success']} |")
    lines += ["", f"c3 seed holdout m=12 %: {_fmt(summary['seed_c3_holdout_m12_pct'])}. Single-seed wins are "
              "reported, not claimed.", "",
              "## Per finalist and control", "",
              "| key | candidates | validation % | dev % | holdout m=12 % | holdout m=11 % | target/14 | gap | "
              "incomplete | audit disagreements | deterministic | m-literals | finalist is seed |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in summary["rows"].items():
        lines.append(f"| {k} | {r['candidates']} | {_fmt(r['validation_pct'])} | {_fmt(r['dev_pct'])} | "
                     f"{_fmt(r['holdout_m12_pct'])} | {_fmt(r['holdout_m11_pct'])} | {r['target_certified']}/"
                     f"{len(target_ids)} | {_fmt(r['gap'])} | {r['holdout_incomplete']} | "
                     f"{r['audit_disagreements']} | {r['deterministic']} | {r['m_literals']} | "
                     f"{r['finalist_is_seed']} |")
    classes = sorted({c for r in summary["rows"].values() for c in r["per_class_m12"]}, key=lambda c: str(c))
    lines += ["", "## Per-class certified counts (m=12 holdout, certified/N)", "",
              "| key | " + " | ".join(str(c) for c in classes) + " |"]
    lines.append("|---|" + "---|" * len(classes))
    for k, r in summary["rows"].items():
        cells = " | ".join(f"{r['per_class_m12'].get(c, [0, 0])[0]}/{r['per_class_m12'].get(c, [0, 0])[1]}"
                           for c in classes)
        lines.append(f"| {k} | {cells} |")
    lines += ["", "An arm claims progress only if it meets both pre-registered success conditions on the mean "
              "over its 3 seeds; single-seed wins are reported, not claimed.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("finalize",))
    ap.add_argument("--run-dir", type=Path, default=ROOT / "autoresearch" / "bound-m-c3-260926")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args(argv)
    print(json.dumps(finalize(args), default=str))


if __name__ == "__main__":
    main()
