"""Post-campaign finalize for corr-cert: freeze finalists, evaluate the holdout m-set
once, audit independently, write finalists/REPORT.md.

Mirrors integrations/lift_finalize.py, adapted for corr-cert's shape: a candidate is
scored per m (4..12 development, 13..20 holdout) rather than per instance, and there
is no per-parent screen/full split or family-attribution concept.

Kept out of integrations/corr_backends.py because the live approval hash covers that
file's bytes. Usage (only after every arm has exited):

    python -m integrations.corr_finalize --run-dir autoresearch/corr-cert-260924
"""
from __future__ import annotations

import argparse
import difflib
from fractions import Fraction as Fr
import json
from pathlib import Path
import re
import shutil
import time

from integrations.corr_backends import CORR_DIR, ROOT, _sha, development_from_manifest

# SkyDiscover 0.2.0 adaevolve/database.py parent-selection labels, verbatim (ported from
# integrations/sort_finalize.py's mode_only_difference). The "balanced" mode inserts no
# label. Which one appears is drawn from an unseeded RNG (random_seed unset in the sky
# config), so an AdaEvolve/EvoX arm's first solution prompt can differ from the approved
# capture in exactly this block and nowhere else.
_GUIDE = "## PARENT SELECTION CONTEXT\n"
MODE_LABELS = (
    _GUIDE + "This parent was selected through diversity-driven sampling to explore different regions.\n\n"
    "### EXPLORATION GUIDANCE\n- Consider alternative algorithmic approaches\n- Don't be constrained by the "
    "parent's approach\n- Look for fundamentally different algorithms or novel techniques\n- Balance creativity "
    "with correctness\n\nYour goal: Discover new approaches that might outperform current solutions.",
    _GUIDE + "This parent was selected from the archive of top-performing programs.\n\n### OPTIMIZATION GUIDANCE\n"
    "- This solution works well, but meaningful improvements are still possible\n- You may refine the existing "
    "approach OR introduce better algorithms\n- Consider: algorithmic improvements, better data structures, "
    "efficient libraries\n- Ensure correctness is maintained\n\nYour goal: Improve upon this solution.",
)
_LABEL_LINES = {line for label in MODE_LABELS for line in label.splitlines()} | {""}


def _strip_mode(text):
    for label in MODE_LABELS:
        text = text.replace(label, "")
    return re.sub(r"\n{3,}", "\n\n", text)


def mode_only_difference(live, captured):
    """(ok, unified_diff, reason): ok iff the two messages arrays differ solely in the
    SkyDiscover mode-guidance block of a user message (every changed line is a label line or
    blank, and the texts are identical once labels are removed); everything else byte-identical."""
    if [m.get("role") for m in live] != [m.get("role") for m in captured]:
        return False, "", "message roles differ"
    diffs = []
    for i, (a, b) in enumerate(zip(live, captured)):
        if a == b:
            continue
        if a.get("role") != "user" or set(a) != set(b) or {k: v for k, v in a.items() if k != "content"} != \
                {k: v for k, v in b.items() if k != "content"}:
            return False, "", f"message {i} ({a.get('role')}) differs outside a user message's content"
        la, lb_ = b["content"].splitlines(), a["content"].splitlines()
        diff = list(difflib.unified_diff(la, lb_, "captured", "live", lineterm="", n=0))
        changed = [x[1:] for x in diff if x[:1] in "+-" and not x.startswith(("+++", "---"))]
        if any(x not in _LABEL_LINES for x in changed):
            return False, "\n".join(diff), f"message {i} changes lines outside the mode-guidance block"
        if _strip_mode(a["content"]) != _strip_mode(b["content"]):
            return False, "\n".join(diff), f"message {i} differs after removing the mode-guidance block"
        diffs.append(f"message {i}:\n" + "\n".join(diff))
    if not diffs:
        return False, "", "no difference: this arm should not be FIRST_PROMPT_MISMATCH"
    return True, "\n".join(diffs), "only the SkyDiscover mode-guidance block differs"


def _parse_first_prompt_md(path: Path):
    """Reconstruct the messages array rendered by corr_backends.write_first_solution_prompt."""
    fence = "`" * 6
    pattern = re.compile(r"## Message \d+: (\S+)\n\n" + fence + r"text\n(.*?)\n" + fence, re.S)
    return [{"role": role, "content": content} for role, content in pattern.findall(Path(path).read_text())]


def _first_solution(paths):
    from integrations.corr_backends import _is_corr_solution_request

    for path in paths:
        receipt = json.loads(Path(path).read_text())
        messages = (receipt.get("forwarded_request_payload") or receipt.get("request_payload") or {}).get(
            "messages", [])
        if messages and _is_corr_solution_request(messages):
            return path, messages
    return None, None


def admit_prompt_mismatch(camp: Path, manifest: dict, ledger_stem: str):
    """Admission record for a FIRST_PROMPT_MISMATCH arm, or (None, reason) to keep it excluded."""
    from integrations.corr_backends import messages_sha256

    engine = manifest.get("engine")
    check = manifest.get("first_solution_prompt_check") or {}
    expected_file, captured_md = camp / f"first-prompt-{engine}.sha256", camp / f"first-prompt-{engine}.md"
    if engine not in ("adaevolve", "evox") or not expected_file.is_file() or not captured_md.is_file():
        return None, "no approved first-prompt capture for this engine"
    expected = expected_file.read_text().split()[0]
    receipts = sorted((camp / f"{ledger_stem}.{engine}.json.receipts").glob("attempt-*.json"))
    live_path, live = _first_solution(receipts)
    if live is None or messages_sha256(live) != check.get("actual_sha256"):
        return None, "live first solution request not found or not the one the guard recorded"
    captured = _parse_first_prompt_md(captured_md)
    if messages_sha256(captured) != expected:
        return None, "captured markdown does not reproduce the approved hash"
    ok, diff, reason = mode_only_difference(live, captured)
    if not ok:
        return None, reason
    return {"rule": "only SkyDiscover's parent-selection mode-guidance block differs; system message, "
                    "program and packet byte-identical (checked by corr_finalize.mode_only_difference)",
            "live_sha256": messages_sha256(live), "captured_sha256": expected,
            "live_receipt": str(live_path), "unified_diff": diff}, reason


def best_from_evaluations(run_dir: Path):
    """(source path, summary, sort key) of the best evaluation record in verified/evaluations,
    for an arm with no verified_best_result (e.g. FIRST_PROMPT_MISMATCH, admitted separately)."""
    best = None
    for res in sorted((run_dir / "verified" / "evaluations").glob("result-*.json")):
        summary = json.loads(res.read_text())["summary"]
        ordinal = int(res.stem.split("-")[1])
        key = (summary["passes"], -Fr(summary["violation_sum"]))
        if best is None or key > best[2]:
            best = (run_dir / "verified" / "evaluations" / f"candidate-{ordinal:04d}.py", summary, key)
    if best is None or _sha(best[0].read_bytes()) != best[1]["candidate_hash"]:
        raise SystemExit(f"abort: no verifiable best evaluation record in {run_dir}")
    return best[0], best[1], best[2]


def _run_raw(source_path: Path, m_values, *, jobs, sandbox):
    """Execute a finalist once per m in the Seatbelt sandbox; keep raw outputs."""
    from concurrent.futures import ThreadPoolExecutor
    from integrations.corr_evaluator import run_program

    source = Path(source_path).read_bytes()
    with ThreadPoolExecutor(max(1, jobs)) as pool:
        return list(pool.map(lambda m: run_program(source, m, 10.0, sandbox), m_values))


def _score_raw(m_values, attempts):
    from integrations.corr_evaluator import score_m

    return [score_m(m, a) for m, a in zip(m_values, attempts)]


def _utc(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _arm_windows(arm_dirs):
    """[start, end] per run dir from its stage (setup) and manifest (finish) file times."""
    out = {}
    for d in arm_dirs:
        start = (d / "stage" / "initial_program.py").stat().st_mtime if (d / "stage" / "initial_program.py").exists() \
            else d.stat().st_mtime
        end = (d / "manifest.json").stat().st_mtime if (d / "manifest.json").exists() else time.time()
        out[d.name] = (_utc(start), _utc(end))
    return out


def _ledger_by_arm(camp: Path, windows, engine_of):
    """Attribute every ledger attempt to the run whose window contains its request time.
    Globs every broker-ledger*.json under camp (e.g. broker-ledger-corr.json and any
    broker-ledger-corr-8k.json from a reasoning-cap change mid-campaign)."""
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
        by_hash[e["candidate_hash"]] = ok and e["invalid"] == 0
    engine = manifest.get("engine")
    me = manifest.get("mechanism_evidence", {})
    if engine == "gepa":
        accepted = max(0, len(me.get("candidate_sha256", [])) - 1)
        how = "GEPA candidates added to its pool"
    elif engine == "sequential":
        accepted = len(me.get("accepted_steps", []))
        how = "greedy screen improvements"
    else:
        # No per-parent screen/full split here (unlike lift): every evaluation is a
        # full development pass, so "accepted" tracks strict combined_score improvements
        # in request order, excluding the seed itself.
        best, accepted = None, 0
        for e in sorted((x for x in trace if x["candidate_hash"] != seed), key=lambda x: x["ordinal"]):
            if best is None or e["combined_score"] > best:
                accepted += 1
                best = e["combined_score"]
        how = "new best combined_score (every valid SkyDiscover child enters the database)"
    rejected = (me.get("model_preflight_failures", 0) if engine == "gepa" else
                sum(1 for r in manifest.get("steps", []) if str(r.get("outcome", "")).startswith("invalid"))
                if engine == "sequential" else me.get("solution_diff_parse_failures", 0))
    return {"proposals_evaluated": len(by_hash), "valid_proposals": sum(by_hash.values()),
            "invalid": len(by_hash) - sum(by_hash.values()) + rejected,
            "accepted": accepted, "accepted_means": how}


def _finalize(args):
    from integrations import corr_audit
    from integrations.corr_evaluator import CONTRACT, VERSION
    from integrations.corr_task import guard_not_holdout, load_m_set

    camp = args.run_dir.resolve()
    out = (args.output or camp / "finalists").resolve()
    fm = (args.frozen_manifest or camp / "frozen" / "manifest.json").resolve()
    frozen = json.loads(fm.read_text())
    holdout = fm.parent / "holdout.json"
    if _sha(holdout.read_bytes()) != frozen["files"]["holdout.json"]:
        raise SystemExit("abort: holdout hash differs from the frozen manifest")
    development, dev_sha = development_from_manifest(fm)
    broker_config_path = camp / "broker-config.json"
    ledger_stem = (Path(json.loads(broker_config_path.read_text())["ledger"]).stem
                   if broker_config_path.is_file() else None)
    # ---- 1. finalists
    runs = {}
    for d in sorted(p for p in camp.glob(args.arms_glob) if (p / "manifest.json").is_file()):
        m = json.loads((d / "manifest.json").read_text())
        admitted = None
        if m.get("status") == "COMPLETE" and m.get("verified_best_result"):
            src = d / "verified" / "best.py"
            if _sha(src.read_bytes()) != m["verified_best_hash"]:
                raise SystemExit(f"abort: {src} does not match its manifest hash")
            key, source_sha256, claim = ((m["verified_best_result"]["passes"],
                                          -Fr(m["verified_best_result"]["violation_sum"])),
                                         m["verified_best_hash"], m["verified_best_result"])
        elif m.get("status") == "FIRST_PROMPT_MISMATCH" and ledger_stem:
            admitted, reason = admit_prompt_mismatch(camp, m, ledger_stem)
            if admitted is None:
                continue
            src, summary, key = best_from_evaluations(d)
            source_sha256, claim = summary["candidate_hash"], {k: summary[k] for k in
                                                                ("passes", "violation_sum", "combined_score")}
        else:
            continue
        if m["engine"] not in runs or key > runs[m["engine"]][0]:
            runs[m["engine"]] = (key, d, m, src, source_sha256, claim, admitted)
    finalists = [{"arm": e, "run_dir": str(d), "source": str(src), "source_sha256": source_sha256,
                  "development_claim": claim,
                  **({"admitted_with_prompt_mismatch": admitted} if admitted else {})}
                 for e, (_, d, m, src, source_sha256, claim, admitted) in sorted(runs.items())]
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
    guard_not_holdout(development)  # sanity: development path must never look like holdout
    sets = {"holdout": holdout, "development": development}
    results = {}
    for name, path in sets.items():
        target = out / f"{name}-results.json"
        if target.exists():  # holdout is evaluated exactly once; later calls reuse it
            results[name] = json.loads(target.read_text())
            continue
        m_values = load_m_set(path)
        per_arm = {}
        for f in finalists:
            start = time.monotonic()
            attempts = _run_raw(srcs[f["arm"]], m_values, jobs=args.jobs, sandbox=not args.no_os_sandbox)
            rows = _score_raw(m_values, attempts)
            (out / "raw").mkdir(exist_ok=True)
            with (out / "raw" / f"{f['arm']}-{name}.jsonl").open("w") as raw:
                for m, a in zip(m_values, attempts):
                    raw.write(json.dumps({"m": m, "status": a.get("status"), "output": a.get("output")}) + "\n")
            per_arm[f["arm"]] = {
                "source_sha256": f["source_sha256"], "m_values": len(rows), "seconds": time.monotonic() - start,
                "passes": sum(r["passed"] for r in rows), "timeouts": sum(r["run"].get("reason") == "time limit"
                                                                          for r in rows),
                "violation_sum": str(sum(Fr(r["magnitude"]) for r in rows if not r["passed"])),
                "results": [{"m": r["m"], "status": r["status"], "passed": r["passed"], "epsilon": r["epsilon"],
                             "magnitude": r["magnitude"]} for r in rows]}
        results[name] = {"set": name, "file_sha256": _sha(path.read_bytes()), "evaluated_utc": _utc(time.time()),
                         "evaluated_once": name == "holdout", "arms": per_arm}
        target.write_text(json.dumps(results[name], default=str) + "\n")
    # ---- 3. independent audit (claimed passes only, re-checked against a fresh corrcert.py)
    audit = {}
    for name in sets:
        audit[name] = {}
        for arm, res in results[name]["arms"].items():
            raw = {}
            for line in (out / "raw" / f"{arm}-{name}.jsonl").open():
                r = json.loads(line)
                raw[r["m"]] = r
            agree, disagree = 0, []
            for r in res["results"]:
                if not r["passed"]:
                    continue
                ok, why = corr_audit.audit_claim(r["m"], raw[r["m"]]["output"])
                if ok:
                    agree += 1
                else:
                    disagree.append({"m": r["m"], "reason": why})
            audit[name][arm] = {"claimed": res["passes"], "agree": agree, "disagree": disagree}
    (out / "audit.json").write_text(json.dumps({"audit": audit}, indent=2) + "\n")
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
    ledger = _ledger_by_arm(camp, _arm_windows(arm_dirs), engine_of)
    report = _report(finalists, runs, results, audit, ledger, frozen_set)
    (out / "REPORT.md").write_text(report)
    return {"output": str(out),
            "passes": {n: {a: v["passes"] for a, v in results[n]["arms"].items()} for n in sets},
            "audit": {n: {a: (v["agree"], len(v["disagree"])) for a, v in d.items()} for n, d in audit.items()}}


def _min_miss_magnitude(res):
    misses = [Fr(r["magnitude"]) for r in res["results"] if not r["passed"]]
    return min(misses) if misses else None


def _report(finalists, runs, results, audit, ledger, frozen_set):
    L = ["# corr-cert campaign finalists (corr-cert-260924)", "",
         f"Evaluator `{frozen_set['evaluator']['version']}`. Development sha256 "
         f"`{frozen_set['development_sha256'][:16]}`, holdout sha256 `{frozen_set['holdout_sha256'][:16]}`. "
         "Holdout was evaluated once, after the finalists were frozen. A pass is an exact THEOREM.md "
         "certificate for that m (corrcert.check_certificate, epsilon < 1). Development is m=4..12, "
         "holdout is m=13..20; passing every development m is not a proof for general m, and the main "
         "conjecture remains open regardless of these results.", "",
         "## Arms", "",
         "| Arm | Model attempts | Valid proposals / evaluated | Invalid / truncated | Accepted | "
         "Dev passes | Holdout passes | Min violation_sum on a miss (dev) | Audit agree (dev / holdout) | "
         "USD (ledger) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    mismatch = []
    for f in finalists:
        arm = f["arm"]
        led = ledger.get(arm, {"attempts": 0, "usd": 0.0, "truncated": 0})
        st = _proposal_stats(runs[arm][2]) if arm in runs else {"proposals_evaluated": "-", "valid_proposals": "-",
                                                                 "accepted": "-", "invalid": "-"}
        d, h = results["development"]["arms"][arm], results["holdout"]["arms"][arm]
        ad, ah = audit["development"][arm], audit["holdout"][arm]
        claim = f.get("development_claim") or {}
        if claim and claim.get("passes") != d["passes"]:
            mismatch.append(f"{arm}: arm run claimed {claim.get('passes')} passes, finalize re-run found {d['passes']}")
        miss = _min_miss_magnitude(d)
        L.append(f"| {arm} | {led['attempts']} | {st['valid_proposals']} / {st['proposals_evaluated']} | "
                 f"{st['invalid']} / {led['truncated']} | {st['accepted']} | {d['passes']}/{d['m_values']} | "
                 f"{h['passes']}/{h['m_values']} | {(f'{float(miss):.3f}' if miss is not None else '-')} | "
                 f"{ad['agree']}/{ad['claimed']} / {ah['agree']}/{ah['claimed']} | {led['usd']:.4f} |")
    L += ["", "Development re-run versus arm claims: " + ("; ".join(mismatch) if mismatch else "all agree.")]
    other = {a: v for a, v in ledger.items() if a not in {f["arm"] for f in finalists}}
    if other:
        L += ["", "Ledger attempts outside the finalist runs: " + "; ".join(
            f"{a}: {v['attempts']} attempts, ${v['usd']:.4f}" for a, v in sorted(other.items()))]
    L += ["", "Accepted means: GEPA candidates added to its pool; sequential greedy screen improvements; "
          "AdaEvolve/EvoX new best combined_score (every valid SkyDiscover child enters the database; "
          "unlike lift there is no per-parent screen/full split here, so this is a strict full-development "
          "improvement, not a screen promotion). Truncated counts provider responses with finish_reason "
          "length.", "", "## Mechanism evidence", ""]
    for arm, (_, d, m, *_rest) in sorted(runs.items()):
        me = m.get("mechanism_evidence", {})
        keep = {k: v for k, v in me.items() if k not in ("reflection_receipts", "candidate_sha256", "lineage")}
        if "lineage" in me:
            keep["lineage_parents"] = me["lineage"].get("parents")
        L.append(f"- **{arm}** (`{Path(d).name}`): `{json.dumps(keep, default=str)[:700]}`")
    dis = [(n, a, x) for n, d in audit.items() for a, v in d.items() for x in v["disagree"]]
    L += ["", "## Independent audit", "",
          "The audit uses integrations/corr_audit.py, which does not import corr_evaluator or corr_task. "
          "It loads a fresh copy of autoresearch/corr-cert-260924/corrcert.py, reimplements the JSON-safe "
          "coefficient-key decoding from scratch, and re-checks (5), (6) and epsilon<1 exactly for every m "
          "an arm claims a pass on.", f"Disagreements: {len(dis)}."] + \
         [f"- {n} {a} m={x['m']}: {x['reason']}" for n, a, x in dis[:20]]
    engine_arms = [a for a in runs if a != "sequential"]
    naive_h, naive_d = results["holdout"]["arms"]["naive-control"]["passes"], \
        results["development"]["arms"]["naive-control"]["passes"]
    best_h = max((results["holdout"]["arms"][a]["passes"] for a in runs), default=None)
    best_d = max((results["development"]["arms"][a]["passes"] for a in runs), default=None)
    new_dev = sorted(m for m in (r["m"] for r in results["development"]["arms"]["naive-control"]["results"])
                     if any(next(rr for rr in results["development"]["arms"][a]["results"] if rr["m"] == m)["passed"]
                            for a in runs)
                     and not next(rr for rr in results["development"]["arms"]["naive-control"]["results"]
                                  if rr["m"] == m)["passed"])
    new_hold = sorted(m for m in (r["m"] for r in results["holdout"]["arms"]["naive-control"]["results"])
                      if any(next(rr for rr in results["holdout"]["arms"][a]["results"] if rr["m"] == m)["passed"]
                             for a in runs)
                      and not next(rr for rr in results["holdout"]["arms"]["naive-control"]["results"]
                                   if rr["m"] == m)["passed"])
    operational = any(_proposal_stats(runs[a][2])["valid_proposals"] > 0 for a in engine_arms)
    L += ["", "## Success levels", "",
          f"- **Operational:** {'yes' if operational else 'no'}. "
          + ("At least one native engine produced valid evolving candidates, with the mechanism traces above."
             if operational else "No native engine produced a valid evaluated proposal."),
          (f"- **Mathematical:** finite only. The finalists certify m in {new_dev} (development) and "
           f"{new_hold} (holdout) that the naive control does not; each is an exact, audited THEOREM.md "
           "certificate for that single m." if new_dev or new_hold else
           "- **Mathematical:** no. The finalists certify no audited m beyond the naive control.") +
          " No universal formula was found or proved for coefficients(m), and the main conjecture "
          "(and Theorem 1 beyond m=16) remains open.",
          f"- **Comparative:** not established. Each arm ran one seed with one model and budget. Best "
          f"development passes among arms is {best_d} against naive {naive_d}; best holdout passes is "
          f"{best_h} against naive {naive_h}. The sequential control is included, but differences are "
          "descriptive and do not rank the engines.",
          "", "## Limitations", "",
          "- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.",
          "- The packet's best-so-far line was stale within some requests: it reflects the verifier state "
          "when the packet was built, not later improvements.",
          "- Truncated proposals (finish_reason length) count as attempted failures and were never repaired.",
          "- AdaEvolve seed copies and migrants carry no evaluator artifacts upstream, so some of its "
          "proposals had no packet.",
          "- Ledger attribution uses run time windows. Spend outside the finalist runs is listed separately.",
          "- Finite development and holdout m-sets only (4..12, 13..20). A miss or timeout proves nothing "
          "about any m, and this evaluates coefficients(m) as given, not any symbolic argument for why it "
          "should hold generally."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True, type=Path, help="campaign directory holding the arm runs")
    ap.add_argument("--arms-glob", default="live-*")
    ap.add_argument("--frozen-manifest", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--seed", type=Path, default=ROOT / "integrations" / "corr_control_f1.py")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-os-sandbox", action="store_true", help="tests only")
    print(json.dumps(_finalize(ap.parse_args(argv)), default=str))


if __name__ == "__main__":
    main()
