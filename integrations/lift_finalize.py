"""Post-campaign finalize for the lift task: freeze finalists, evaluate the holdout once,
audit independently, write finalists/REPORT.md.

Kept out of integrations/lift_backends.py because the live approval hash covers that
file's bytes. Usage (only after every arm has exited):

    python -m integrations.lift_finalize --run-dir autoresearch/lift-m9-260924
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Fr
import json
from pathlib import Path
import shutil
import time

from integrations.lift_backends import ROOT, _sha, development_from_manifest


def _run_raw(source_path: Path, instances, *, jobs, sandbox):
    """Execute a finalist once per instance in the Seatbelt sandbox; keep raw outputs."""
    from concurrent.futures import ThreadPoolExecutor
    from integrations.lift_evaluator import run_program

    source = Path(source_path).read_bytes()
    with ThreadPoolExecutor(jobs) as pool:
        return list(pool.map(lambda x: run_program(source, x[0], 10.0, sandbox), instances))


def _score_raw(instances, attempts, jobs):
    from concurrent.futures import ProcessPoolExecutor
    from integrations.lift_evaluator import _score

    args = [(inst, rows, a) for (inst, rows), a in zip(instances, attempts)]
    with ProcessPoolExecutor(jobs) as pool:
        return list(pool.map(_score, args, chunksize=16))


def _utc(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _arm_windows(camp: Path, arm_dirs):
    """[start, end] per run dir from its stage (setup) and manifest (finish) file times."""
    out = {}
    for d in arm_dirs:
        start = (d / "stage" / "initial_program.py").stat().st_mtime if (d / "stage" / "initial_program.py").exists() \
            else d.stat().st_mtime
        end = (d / "manifest.json").stat().st_mtime if (d / "manifest.json").exists() else time.time()
        out[d.name] = (_utc(start), _utc(end))
    return out


def _ledger_by_arm(camp: Path, windows, engine_of):
    """Attribute every ledger attempt to the run whose window contains its request time."""
    rows = {}
    for ledger in sorted(camp.glob("broker-ledger*.json")):
        state = json.loads(ledger.read_text())
        for a in state.get("attempts", []):
            receipt = Path(a.get("receipt_path") or "")
            at = json.loads(receipt.read_text()).get("request_at_utc") if receipt.is_file() else None
            finish = json.loads(receipt.read_text()).get("finish_reason") if receipt.is_file() else None
            run = next((r for r, (s, e) in windows.items() if at and s <= at <= e), None)
            arm = engine_of.get(run, "unattributed")
            row = rows.setdefault(arm, {"attempts": 0, "usd": 0.0, "truncated": 0, "errors": 0, "ledgers": set()})
            row["attempts"] += 1
            row["usd"] += a.get("charged_usd") or 0.0
            row["truncated"] += finish in ("length", "max_tokens")
            row["errors"] += a.get("status") != "ok"
            row["ledgers"].add(ledger.name)
    for row in rows.values():
        row["ledgers"] = sorted(row["ledgers"])
    return rows


def _proposal_stats(manifest):
    seed = manifest.get("seed_sha256")
    trace = manifest.get("evaluation_trace", [])
    by_hash = {}
    for e in trace:
        if e["candidate_hash"] == seed:
            continue
        ok = by_hash.get(e["candidate_hash"], True)
        by_hash[e["candidate_hash"]] = ok and e["valid"] == e["instances"]
    engine = manifest.get("engine")
    me = manifest.get("mechanism_evidence", {})
    if engine == "gepa":
        accepted = max(0, len(me.get("candidate_sha256", [])) - 1)
        how = "GEPA candidates added to its pool"
    elif engine == "sequential":
        accepted = len(me.get("accepted_steps", []))
        how = "greedy screen improvements"
    else:
        best, accepted = None, 0
        for e in trace:
            if e["scope"] == "screen" and e["valid"] == e["instances"]:
                if best is not None and e["combined_score"] > best and e["candidate_hash"] != seed:
                    accepted += 1
                best = e["combined_score"] if best is None else max(best, e["combined_score"])
        how = "new best screen score (all SkyDiscover children enter the database)"
    rejected = (me.get("model_preflight_failures", 0) if engine == "gepa" else
                sum(1 for r in manifest.get("steps", []) if str(r.get("outcome", "")).startswith("invalid"))
                if engine == "sequential" else me.get("solution_diff_parse_failures", 0))
    return {"proposals_evaluated": len(by_hash), "valid_proposals": sum(by_hash.values()),
            "invalid": len(by_hash) - sum(by_hash.values()) + rejected,
            "accepted": accepted, "accepted_means": how}


def _finalize(args):
    from integrations import lift_audit
    from integrations.lift_evaluator import CONTRACT, VERSION, load_instances

    camp = args.run_dir.resolve()
    out = (args.output or camp / "finalists").resolve()
    fm = (args.frozen_manifest or camp / "frozen" / "manifest.json").resolve()
    frozen = json.loads(fm.read_text())
    holdout = fm.parent / "holdout.json"
    if _sha(holdout.read_bytes()) != frozen["files"]["holdout.json"]:
        raise SystemExit("abort: holdout hash differs from the frozen manifest")
    development, dev_sha = development_from_manifest(fm)
    # ---- 1. finalists
    runs = {}
    for d in sorted(p for p in camp.glob(args.arms_glob) if (p / "manifest.json").is_file()):
        m = json.loads((d / "manifest.json").read_text())
        if m.get("status") != "COMPLETE" or not m.get("verified_best_full"):
            continue
        src = d / "verified" / "best.py"
        if _sha(src.read_bytes()) != m["verified_best_hash"]:
            raise SystemExit(f"abort: {src} does not match its manifest hash")
        key = (m["verified_best_full"]["certificates"], -Fr(m["verified_best_full"]["gap_sum"]))
        if m["engine"] not in runs or key > runs[m["engine"]][0]:
            runs[m["engine"]] = (key, d, m, src)
    finalists = [{"arm": e, "run_dir": str(d), "source": str(src), "source_sha256": m["verified_best_hash"],
                  "development_claim": m["verified_best_full"]} for e, (_, d, m, src) in sorted(runs.items())]
    seed = args.seed.resolve()
    finalists.append({"arm": "naive-control", "run_dir": None, "source": str(seed),
                      "source_sha256": _sha(seed.read_bytes()), "development_claim": None})
    frozen_set = {"finalists": [{k: f[k] for k in ("arm", "source_sha256")} for f in finalists],
                  "holdout_sha256": frozen["files"]["holdout.json"], "development_sha256": dev_sha,
                  "frozen_manifest_sha256": _sha(fm.read_bytes()), "evaluator": {"version": VERSION,
                                                                                 "contract": CONTRACT}}
    out.mkdir(parents=True, exist_ok=True)
    (out / "sources").mkdir(exist_ok=True)
    mpath = out / "manifest.json"
    if mpath.exists():
        old = json.loads(mpath.read_text())
        if {k: old.get(k) for k in frozen_set} != frozen_set:
            raise SystemExit("refusing: finalists/manifest.json is frozen with different hashes")
    else:
        for f in finalists:
            shutil.copyfile(f["source"], out / "sources" / f"{f['arm']}.py")
        mpath.write_text(json.dumps(dict(frozen_set, created_utc=_utc(time.time()), details=finalists),
                                    indent=2, default=str) + "\n")
    srcs = {f["arm"]: out / "sources" / f"{f['arm']}.py" for f in finalists}
    for f in finalists:
        if _sha(srcs[f["arm"]].read_bytes()) != f["source_sha256"]:
            raise SystemExit(f"abort: frozen source copy for {f['arm']} changed")
    # ---- 2. holdout once, development re-run (raw outputs kept for the audit)
    sets = {"holdout": holdout, "development": development}
    raw_instances = {name: {i["id"]: i for i in json.loads(p.read_text())["instances"]} for name, p in sets.items()}
    results = {}
    for name, path in sets.items():
        target = out / f"{name}-results.json"
        if target.exists():  # holdout is evaluated exactly once; later calls reuse it
            results[name] = json.loads(target.read_text())
            continue
        loaded = load_instances(path)
        per_arm = {}
        for f in finalists:
            start = time.monotonic()
            attempts = _run_raw(srcs[f["arm"]], loaded, jobs=args.jobs, sandbox=not args.no_os_sandbox)
            rows = _score_raw(loaded, attempts, args.jobs)
            (out / "raw").mkdir(exist_ok=True)
            with (out / "raw" / f"{f['arm']}-{name}.jsonl").open("w") as raw:
                for (inst, _), a in zip(loaded, attempts):
                    raw.write(json.dumps({"id": inst["id"], "status": a["status"], "output": a.get("output")}) + "\n")
            per_arm[f["arm"]] = {
                "source_sha256": f["source_sha256"], "instances": len(rows), "seconds": time.monotonic() - start,
                "certificates": sum(r["status"] == "CERTIFICATE" for r in rows),
                "valid": sum(r["valid"] for r in rows), "timeouts": sum(r["run"].get("reason") == "time limit" for r in rows),
                "gap_sum": str(sum(Fr(r["gap"]) for r in rows)),
                "results": [{"id": r["id"], "child_id": r["child_id"], "status": r["status"],
                             "certificate": r["certificate"]} for r in rows]}
        results[name] = {"set": name, "file_sha256": _sha(path.read_bytes()), "evaluated_utc": _utc(time.time()),
                         "evaluated_once": name == "holdout", "arms": per_arm}
        target.write_text(json.dumps(results[name], default=str) + "\n")
    # ---- 3. independent audit + family attribution
    audit = {}
    for name in sets:
        audit[name] = {}
        for arm, res in results[name]["arms"].items():
            raw = {}
            for line in (out / "raw" / f"{arm}-{name}.jsonl").open():
                r = json.loads(line)
                raw[r["id"]] = r
            agree, disagree = 0, []
            for r in res["results"]:
                if r["status"] != "CERTIFICATE":
                    continue
                ok, why = lift_audit.audit_claim(raw_instances[name][r["id"]], raw[r["id"]]["output"], r["certificate"])
                if ok:
                    agree += 1
                else:
                    disagree.append({"id": r["id"], "reason": why})
            audit[name][arm] = {"claimed": res["certificates"], "agree": agree, "disagree": disagree}
    families = {}
    for name in sets:
        certified = {arm: {r["child_id"] for r in res["results"] if r["status"] == "CERTIFICATE"}
                     - {raw_instances[name][d["id"]]["child"]["id"] for d in audit[name][arm]["disagree"]}
                     for arm, res in results[name]["arms"].items()}
        naive = certified.get("naive-control", set())
        union = set().union(*(v for a, v in certified.items() if a != "naive-control")) if len(certified) > 1 else set()
        extra = sorted(union - naive)
        families[name] = {"naive": len(naive), "union_of_finalists": len(union), "union_with_naive": len(union | naive),
                          "not_certified_by_naive": [{"child_id": c, "arms": sorted(a for a, v in certified.items()
                                                                                    if c in v and a != "naive-control")}
                                                     for c in extra],
                          "per_arm_distinct": {a: len(v) for a, v in certified.items()}}
    (out / "audit.json").write_text(json.dumps({"audit": audit, "families": families}, indent=2) + "\n")
    # ---- 4. report
    arm_dirs = sorted(p for p in camp.glob(args.arms_glob) if p.is_dir())
    engine_of = {}
    manifests = {}
    for d in arm_dirs:
        if (d / "manifest.json").is_file():
            mm = json.loads((d / "manifest.json").read_text())
            engine_of[d.name] = mm.get("engine")
            manifests[d.name] = mm
        else:
            engine_of[d.name] = d.name.split("-")[1] if "-" in d.name else d.name
    ledger = _ledger_by_arm(camp, _arm_windows(camp, arm_dirs), engine_of)
    report = _report(finalists, runs, results, audit, families, ledger, manifests, frozen_set)
    (out / "REPORT.md").write_text(report)
    return {"output": str(out), "families": {k: {x: v[x] for x in ("naive", "union_of_finalists")}
                                             for k, v in families.items()},
            "audit": {n: {a: (v["agree"], len(v["disagree"])) for a, v in d.items()} for n, d in audit.items()}}


def _report(finalists, runs, results, audit, families, ledger, manifests, frozen_set):
    L = ["# Lift campaign finalists (lift-m9-260924)", "",
         f"Evaluator `{frozen_set['evaluator']['version']}`. Development sha256 `{frozen_set['development_sha256'][:16]}`, "
         f"holdout sha256 `{frozen_set['holdout_sha256'][:16]}`. Holdout was evaluated once, after the finalists "
         "were frozen. Certificates are finite: exact bounds for listed m=9 unit-base families (all block "
         "lengths via Lemma 1). They are not a proof of the conjecture or of a lifting lemma.", "",
         "## Arms", "",
         "| Arm | Model attempts | Valid proposals / evaluated | Invalid / truncated | Accepted | Dev certificates | "
         "Holdout certificates | Audit agree (dev / holdout) | USD (ledger) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    mismatch = []
    for f in finalists:
        arm = f["arm"]
        led = ledger.get(arm, {"attempts": 0, "usd": 0.0, "truncated": 0})
        st = _proposal_stats(runs[arm][2]) if arm in runs else {"proposals_evaluated": "-", "valid_proposals": "-",
                                                                 "accepted": "-", "invalid": "-"}
        d, h = results["development"]["arms"][arm], results["holdout"]["arms"][arm]
        ad, ah = audit["development"][arm], audit["holdout"][arm]
        claim = f.get("development_claim") or {}
        if claim and claim.get("instances") != d["instances"]:
            mismatch.append(f"{arm}: not comparable (claim on {claim.get('instances')} instances, re-run on {d['instances']})")
        elif claim and claim["certificates"] != d["certificates"]:
            mismatch.append(f"{arm}: arm run claimed {claim['certificates']}, finalize re-run found {d['certificates']}")
        L.append(f"| {arm} | {led['attempts']} | {st['valid_proposals']} / {st['proposals_evaluated']} | "
                 f"{st['invalid']} / {led['truncated']} | {st['accepted']} | {d['certificates']}/{d['instances']} | "
                 f"{h['certificates']}/{h['instances']} | {ad['agree']}/{ad['claimed']} / {ah['agree']}/{ah['claimed']} | "
                 f"{led['usd']:.4f} |")
    L += ["", "Development re-run versus arm claims: " + ("; ".join(mismatch) if mismatch else "all agree.")]
    other = {a: v for a, v in ledger.items() if a not in {f["arm"] for f in finalists}}
    if other:
        L += ["", "Ledger attempts outside the finalist runs: " + "; ".join(
            f"{a}: {v['attempts']} attempts, ${v['usd']:.4f}" for a, v in sorted(other.items()))]
    L += ["", "Accepted means: GEPA candidates added to its pool; sequential greedy screen improvements; "
          "AdaEvolve/EvoX new best screen scores (every valid SkyDiscover child enters the database). "
          "Truncated counts provider responses with finish_reason length.", "", "## Mechanism evidence", ""]
    for arm, (_, d, m, _) in sorted(runs.items()):
        me = m.get("mechanism_evidence", {})
        keep = {k: v for k, v in me.items() if k not in ("reflection_receipts", "candidate_sha256", "lineage")}
        if "lineage" in me:
            keep["lineage_parents"] = me["lineage"].get("parents")
        L.append(f"- **{arm}** (`{Path(d).name}`): `{json.dumps(keep, default=str)[:700]}`")
    L += ["", "## Families", ""]
    for name in ("development", "holdout"):
        fam = families[name]
        L.append(f"- **{name}**: naive certifies {fam['naive']} child families. The union of engine finalists "
                 f"certifies {fam['union_of_finalists']}, and {len(fam['not_certified_by_naive'])} of those are "
                 f"not certified by naive. Per arm: {fam['per_arm_distinct']}.")
    L += ["", "Families certified by a finalist but not by naive (holdout first; at most 40 per set):", ""]
    for name in ("holdout", "development"):
        for row in families[name]["not_certified_by_naive"][:40]:
            L.append(f"- {name}: `{row['child_id']}` by {', '.join(row['arms'])}")
    dis = [(n, a, x) for n, d in audit.items() for a, v in d.items() for x in v["disagree"]]
    L += ["", "## Independent audit", "",
          "The audit uses integrations/lift_audit.py, which does not import the evaluator. It loads the independent "
          "m=8 checker with M=9 and rebuilds each child from the parent. It replays every returned word, checks the "
          "Lemma 1 lift at z=0, e_j, 2e_j and all adjacent pairs, and checks the claimed exact mixture witness.",
          f"Disagreements: {len(dis)}."] + [f"- {n} {a} `{x['id']}`: {x['reason']}" for n, a, x in dis[:20]]
    engine_arms = [a for a in runs if a != "sequential"]
    naive_h = results["holdout"]["arms"]["naive-control"]["certificates"]
    best_h = max((results["holdout"]["arms"][a]["certificates"] for a in runs), default=None)
    agreed_new = len(families["holdout"]["not_certified_by_naive"]) + len(families["development"]["not_certified_by_naive"])
    operational = any(_proposal_stats(runs[a][2])["valid_proposals"] > 0 for a in engine_arms)
    L += ["", "## Success levels", "",
          f"- **Operational:** {'yes' if operational else 'no'}. "
          + ("At least one native engine produced valid evolving candidates, with the mechanism traces above."
             if operational else "No native engine produced a valid evaluated proposal."),
          (f"- **Mathematical:** finite only. The finalists certify {agreed_new} audited m=9 unit-base child "
           "families (development plus holdout) that the naive control does not. Each is an exact family bound."
           if agreed_new else "- **Mathematical:** no. The finalists certify no audited family beyond the naive "
           "control.") + " No uniform label-insertion lemma was found or proved, and the conjecture remains open.",
          f"- **Comparative:** not established. Each arm ran one seed with one model and budget. The best "
          f"holdout count among arms is {best_h}, against naive {naive_h}. The sequential control is included, but "
          "differences are descriptive and do not rank the engines.",
          "", "## Limitations", "",
          "- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.",
          "- The packet's best-so-far line was stale within some requests: it reflects the verifier state when "
          "the packet was built, not later improvements.",
          "- 4096-token output truncations are concentrated on long programs. Truncated proposals count as "
          "attempted failures and were never repaired.",
          "- AdaEvolve seed copies and migrants carry no evaluator artifacts upstream, so some of its proposals "
          "had no packet.",
          "- Ledger attribution uses run time windows. Spend outside the finalist runs is listed separately.",
          "- Finite development and holdout families only. A miss or timeout proves nothing."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True, type=Path, help="campaign directory holding the arm runs")
    ap.add_argument("--arms-glob", default="live-*")
    ap.add_argument("--frozen-manifest", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--seed", type=Path, default=ROOT / "integrations" / "lift_control_naive.py")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-os-sandbox", action="store_true", help="tests only")
    print(json.dumps(_finalize(ap.parse_args(argv)), default=str))


if __name__ == "__main__":
    main()
