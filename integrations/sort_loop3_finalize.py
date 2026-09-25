"""Finalize loop v3 (sort-m9-v3-260925): one finalist per (arm, seed), one holdout pass, mean and spread.

Finalists are the verified best (full development combined score) of each finished
live-v3-{arm}-s{S}-* run (COMPLETE, or EVAL_BUDGET/GUARD_STOPPED with a verified best; the
status is shown); the first such run per (arm, seed) is used, never the best
of several, and never a best-of-seeds. Runs that ended FIRST_PROMPT_MISMATCH,
STRATEGY_EVOLUTION_LEAK, INCOMPLETE or BROKER_STOPPED are listed as excluded. Sources and
the manifest (with this file's sha256) are frozen before the holdout is loaded; each
finalist and control is evaluated on the holdout exactly once, and later calls reuse the
hash-checked results file. The report is descriptive: with n = 3 the strongest wording is
"consistent in 3 of 3 seeds", never significance.

    python -m integrations.sort_loop3_finalize --run-dir autoresearch/sort-m9-v3-260925
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import statistics
import time

from integrations.sort_backends import ROOT, _sha

ARMS = ("gepa", "sequential", "adaevolve", "evox")
ROW_KEYS = ("id", "m", "r", "d", "budget", "status", "valid", "within", "length", "excess", "slack", "word", "final")
RES_KEYS = ("states", "within_budget", "within_fraction", "min_r_within_rate", "worst_r", "valid", "invalid",
            "mean_excess", "max_excess", "timeouts", "incomplete", "combined_score", "per_r", "candidate_hash")
GAP_FLAG = 0.03
EXCLUDED = ("FIRST_PROMPT_MISMATCH", "STRATEGY_EVOLUTION_LEAK", "INCOMPLETE", "BROKER_STOPPED")
METRICS = ("holdout_within", "holdout_worst_r_rate", "holdout_m9r6", "holdout_m10r3", "holdout_mean_excess",
           "dev_within", "dev_combined", "flash_usd", "reflection_usd", "flash_calls", "reflection_calls",
           "truncations", "accepted", "memorization_gap")


def _utc(ts=None):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc).isoformat()


def spread(values) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {"n": len(vals), "mean": statistics.fmean(vals), "sd": statistics.stdev(vals) if len(vals) > 1 else None,
            "min": min(vals), "max": max(vals)}


def discover_runs(camp: Path, glob="live-v3-*"):
    """(finalist runs keyed by (arm, seed), excluded list). First COMPLETE run per (arm, seed) wins."""
    chosen, excluded = {}, []
    for d in sorted(p for p in Path(camp).glob(glob) if (p / "manifest.json").is_file()):
        m = json.loads((d / "manifest.json").read_text())
        key = (m.get("engine"), m.get("seed"))
        entry = {"run": d.name, "arm": key[0], "seed": key[1], "status": m.get("status")}
        if m.get("status") in EXCLUDED or not m.get("verified_best_result"):
            excluded.append(dict(entry, reason=f"status {m.get('status')}"))
        elif key in chosen:
            excluded.append(dict(entry, reason="duplicate finished run for this (arm, seed); the first is used"))
        else:
            chosen[key] = (d, m)
    return chosen, excluded


def memorization_gap(dev_rows, revealed_ids) -> dict:
    revealed = set(revealed_ids or ())
    a = [r for r in dev_rows if r["id"] in revealed]
    b = [r for r in dev_rows if r["id"] not in revealed]
    ra = sum(r["within"] for r in a) / len(a) if a else None
    rb = sum(r["within"] for r in b) / len(b) if b else None
    gap = None if ra is None or rb is None else ra - rb
    return {"revealed_states": len(a), "revealed_within_rate": ra, "unrevealed_states": len(b),
            "unrevealed_within_rate": rb, "gap": gap, "flag": gap is not None and gap > GAP_FLAG}


def ledger_path(camp: Path, arm, seed, manifest=None, kind="flash"):
    """The run's ledger: the manifest's path (written by sort_loop3._live_v3), else _live_v3's naming
    broker-ledger-v3[-reflection].{arm}-s{seed}.json. A manifest reflection_ledger of None means no reflection
    broker ran (returns False)."""
    key = "ledger" if kind == "flash" else "reflection_ledger"
    if manifest is not None and key in manifest:
        value = manifest[key]
        if value is None:
            return False
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    from integrations.sort_loop3 import ledger_paths

    return ledger_paths(camp, arm, seed)[0 if kind == "flash" else 1]


def ledger_stats(camp: Path, arm, seed, manifest=None) -> dict:
    """USD, calls and truncations per broker; None when the ledger file is missing (never a silent 0)."""
    out = {}
    for label in ("flash", "reflection"):
        path = ledger_path(camp, arm, seed, manifest, label)
        if path is False:
            usd = calls = trunc = 0
        elif not path.is_file():
            usd = calls = trunc = None
        else:
            usd = calls = trunc = 0
            for a in json.loads(path.read_text()).get("attempts", []):
                calls += 1
                usd += a.get("charged_usd") or 0.0
                receipt = Path(a.get("receipt_path") or "")
                if receipt.is_file() and json.loads(receipt.read_text()).get("finish_reason") in ("length", "max_tokens"):
                    trunc += 1
        out.update({f"{label}_usd": usd, f"{label}_calls": calls, f"{label}_truncations": trunc})
    return out


def accepted_proposals(m) -> int:
    me = m.get("mechanism_evidence") or {}
    if m.get("engine") == "gepa":
        return max(0, len(me.get("candidate_sha256") or []) - 1)
    if m.get("engine") == "sequential":
        return len(me.get("accepted_steps") or [])
    best, n = None, 0
    seed = (m.get("seed_result") or {}).get("combined_score")
    for row in sorted(m.get("evaluation_trace") or [], key=lambda r: r["ordinal"]):
        if row["scope"] != "full" or row.get("final"):
            continue
        if best is None:
            best = seed
        if row["combined_score"] > best:
            n, best = n + 1, row["combined_score"]
    return n


def _eval_once(target: Path, set_path: Path, states, sources: dict, *, sandbox, jobs, name):
    from integrations import sort_evaluator as E

    if target.exists():
        res = json.loads(target.read_text())
        if res["file_sha256"] != _sha(set_path.read_bytes()):
            raise SystemExit(f"abort: {name} changed since its recorded evaluation")
        if set(res["arms"]) != set(sources):
            raise SystemExit(f"abort: {target.name} was recorded for different finalists")
        return res
    per = {}
    for label, src in sources.items():
        r = E.evaluate(src, states, require_os_sandbox=sandbox, jobs=jobs)
        per[label] = dict({k: r[k] for k in RES_KEYS}, rows=[{k: x.get(k) for k in ROW_KEYS} for x in r["results"]])
    res = {"set": name, "file_sha256": _sha(set_path.read_bytes()), "evaluated_utc": _utc(),
           "evaluated_once": name == "holdout", "arms": per}
    target.write_text(json.dumps(res) + "\n")
    return res


def finalize(camp: Path, *, frozen_manifest: Path, out: Path | None = None, naive: Path, sweep: Path, jobs=8,
             sandbox=True, v2_reference: Path | None = None, glob="live-v3-*", audit=True) -> dict:
    from integrations import sort_audit
    from integrations import sort_evaluator as E
    from integrations.lift_backends import development_from_manifest

    camp, fm = Path(camp).resolve(), Path(frozen_manifest).resolve()
    out = Path(out or camp / "finalists").resolve()
    frozen = json.loads(fm.read_text())
    holdout = fm.parent / "holdout.json"
    if _sha(holdout.read_bytes()) != frozen["files"]["holdout.json"]:
        raise SystemExit("abort: holdout hash differs from the frozen manifest")
    development, dev_sha = development_from_manifest(fm)
    chosen, excluded = discover_runs(camp, glob)
    finalists = []
    for (arm, seed), (d, m) in sorted(chosen.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        src = d / "verified" / "best.py"
        if _sha(src.read_bytes()) != m["verified_best_hash"]:
            raise SystemExit(f"abort: {src} does not match its manifest hash")
        finalists.append({"label": f"{arm}-s{seed}", "arm": arm, "seed": seed, "run_dir": str(d), "source": str(src),
                          "source_sha256": m["verified_best_hash"], "development_claim": m["verified_best_result"],
                          "revealed_ids": m.get("revealed_ids") or [], "status": m.get("status")})
    for label, path in (("naive-control", naive), ("sweep-control", sweep)):
        finalists.append({"label": label, "arm": label, "seed": None, "run_dir": None, "source": str(Path(path).resolve()),
                          "source_sha256": _sha(Path(path).read_bytes()), "development_claim": None, "revealed_ids": []})
    frozen_set = {"finalists": [{k: f[k] for k in ("label", "source_sha256")} for f in finalists],
                  "holdout_sha256": frozen["files"]["holdout.json"], "development_sha256": dev_sha,
                  "frozen_manifest_sha256": _sha(fm.read_bytes()),
                  "finalize_sha256": _sha(Path(__file__).read_bytes()),
                  "evaluator": {"version": E.VERSION, "contract": E.CONTRACT, "hash": E.evaluator_hash()}}
    (out / "sources").mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    if mpath.exists():
        old = json.loads(mpath.read_text())
        if {k: old.get(k) for k in frozen_set} != frozen_set:
            raise SystemExit("refusing: finalists/manifest.json is frozen with different hashes")
    else:
        for f in finalists:
            shutil.copyfile(f["source"], out / "sources" / f"{f['label']}.py")
        mpath.write_text(json.dumps(dict(frozen_set, created_utc=_utc(), details=finalists, excluded=excluded),
                                    indent=2, default=str) + "\n")
    srcs = {f["label"]: out / "sources" / f"{f['label']}.py" for f in finalists}
    for f in finalists:
        if _sha(srcs[f["label"]].read_bytes()) != f["source_sha256"]:
            raise SystemExit(f"abort: frozen source copy for {f['label']} changed")
    E.guard_not_holdout(development)
    sets = {"holdout": (holdout, E.load_set(holdout, allow_holdout=True)),
            "development": (development, E.load_set(development))}
    results = {n: _eval_once(out / f"{n}-results.json", p, st, srcs, sandbox=sandbox, jobs=jobs, name=n)
               for n, (p, st) in sets.items()}
    audits = {}
    if audit:
        tables = {(t["m"], t["r"]): (ROOT / Path(t["path"]).parent, t["table_sha256"]) for t in frozen["tables"]}
        for name, (_, states) in sets.items():
            by_id = {s["id"]: s for s in states}
            audits[name] = sort_audit.audit(by_id, {a: v["rows"] for a, v in results[name]["arms"].items()}, tables)
        (out / "audit.json").write_text(json.dumps({"audit": audits}, indent=2) + "\n")
    rows = {}
    for f in finalists:
        h, dv = results["holdout"]["arms"][f["label"]], results["development"]["arms"][f["label"]]
        row = {"label": f["label"], "arm": f["arm"], "seed": f["seed"], "run_status": f.get("status"),
               "holdout_within": h["within_budget"],
               "holdout_states": h["states"], "holdout_worst_r_rate": h["min_r_within_rate"],
               "holdout_m9r6": h["per_r"].get("m9r6", {}).get("within"),
               "holdout_m10r3": h["per_r"].get("m10r3", {}).get("within"), "holdout_mean_excess": h["mean_excess"],
               "dev_within": dv["within_budget"], "dev_combined": dv["combined_score"]}
        gap = memorization_gap(dv["rows"], f["revealed_ids"])
        row.update(memorization=gap, memorization_gap=gap["gap"])
        if f["run_dir"]:
            m = json.loads((Path(f["run_dir"]) / "manifest.json").read_text())
            ls = ledger_stats(camp, f["arm"], f["seed"], m)
            parts = (ls["flash_truncations"], ls["reflection_truncations"])
            row.update(ls, truncations=None if None in parts else sum(parts), accepted=accepted_proposals(m))
        rows[f["label"]] = row
    per_arm = {arm: dict({k: spread([r.get(k) for r in rows.values() if r["arm"] == arm]) for k in METRICS},
                         seeds=sorted(r["seed"] for r in rows.values() if r["arm"] == arm))
               for arm in ARMS if any(r["arm"] == arm for r in rows.values())}
    paired = {}
    seq = {r["seed"]: r for r in rows.values() if r["arm"] == "sequential"}
    for r in rows.values():
        if r["arm"] in ARMS and r["arm"] != "sequential" and r["seed"] in seq:
            paired.setdefault(r["arm"], {})[r["seed"]] = {
                k: r[k] - seq[r["seed"]][k] for k in ("holdout_within", "holdout_m9r6", "holdout_m10r3")
                if r.get(k) is not None and seq[r["seed"]].get(k) is not None}
    v2 = None
    if v2_reference and Path(v2_reference).is_file():
        ref = json.loads(Path(v2_reference).read_text())["arms"]
        v2 = {a: {"holdout_within": v["within_budget"], "holdout_m9r6": v["per_r"].get("m9r6", {}).get("within"),
                  "holdout_m10r3": v["per_r"].get("m10r3", {}).get("within")} for a, v in ref.items()}
    summary = {"rows": rows, "per_arm": per_arm, "paired_vs_sequential": paired, "excluded": excluded,
               "v2_single_seed_reference": v2,
               "audit": {n: {a: (v["agree"], len(v["disagree"])) for a, v in d.items()} for n, d in audits.items()}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (out / "REPORT.md").write_text(report(summary))
    return summary


def _f(x, nd=2):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def report(s) -> str:
    L = ["# sort-m9 loop v3 finalists (descriptive)", "",
         "One finalist per (arm, seed): the verified best by full development combined score of the first COMPLETE "
         "run. Holdout evaluated once. With n <= 3 seeds, the strongest allowed wording is \"consistent in k of k "
         "seeds\"; no significance claims. Every valid within-budget word is an exact certificate d(v) <= T for that "
         "state only.", "", "## Per arm over seeds (n, mean, SD, min, max)", "",
         "| Arm | Metric | n | mean | SD | min | max |", "|---|---|---:|---:|---:|---:|---:|"]
    for arm, d in s["per_arm"].items():
        for k in METRICS:
            v = d[k]
            L.append(f"| {arm} | {k} | {v['n']} | {_f(v['mean'])} | {_f(v['sd'])} | {_f(v['min'])} | {_f(v['max'])} |")
    L += ["", "## Per finalist", "", "| Label | Holdout within | worst-r | (9,6) | (10,3) | Dev within | Dev combined | "
          "Mem. gap | Flag |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in s["rows"].values():
        L.append(f"| {r['label']} | {r['holdout_within']}/{r['holdout_states']} | {_f(r['holdout_worst_r_rate'])} | "
                 f"{_f(r['holdout_m9r6'])} | {_f(r['holdout_m10r3'])} | {r['dev_within']} | {_f(r['dev_combined'], 4)} | "
                 f"{_f(r['memorization_gap'], 3)} | {'GAP > 0.03' if r['memorization']['flag'] else ''} |")
    L += ["", "## Paired differences against sequential (arm minus sequential, per seed; no tests)", ""]
    for arm, by_seed in s["paired_vs_sequential"].items():
        for seed, diff in sorted(by_seed.items()):
            L.append(f"- {arm} s{seed}: " + ", ".join(f"{k} {v:+d}" if isinstance(v, int) else f"{k} {v:+.3f}"
                                                    for k, v in diff.items()))
    if s["v2_single_seed_reference"]:
        L += ["", "## v2 single-seed reference (sort-m9-260925, one seed each)", ""]
        for a, v in s["v2_single_seed_reference"].items():
            L.append(f"- {a}: holdout within {v['holdout_within']}, (9,6) {v['holdout_m9r6']}, (10,3) {v['holdout_m10r3']}")
    L += ["", "## Excluded runs", ""] + ([f"- {e['run']} ({e['arm']} s{e['seed']}): {e['reason']}" for e in s["excluded"]]
                                          or ["- none"])
    L += ["", "## Independent audit (agree, disagree)", "", f"{s['audit']}", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", type=Path, default=ROOT / "autoresearch" / "sort-m9-v3-260925")
    ap.add_argument("--frozen-manifest", type=Path, default=ROOT / "autoresearch" / "sort-m9-260925" / "frozen" /
                    "manifest.json")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--naive", type=Path, default=ROOT / "integrations" / "sort_control_naive.py")
    ap.add_argument("--sweep", type=Path, default=ROOT / "integrations" / "sort_control_sweep.py")
    ap.add_argument("--v2-reference", type=Path, default=ROOT / "autoresearch" / "sort-m9-260925" / "finalists" /
                    "holdout-results.json")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    s = finalize(a.run_dir, frozen_manifest=a.frozen_manifest, out=a.output, naive=a.naive, sweep=a.sweep,
                 jobs=a.jobs, v2_reference=a.v2_reference)
    print(json.dumps({"finalists": list(s["rows"]), "excluded": len(s["excluded"]), "audit": s["audit"]}))


if __name__ == "__main__":
    main()
