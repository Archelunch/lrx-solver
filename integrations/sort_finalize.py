"""Post-campaign finalize for sort-m9: freeze finalists, evaluate the holdout once,
audit independently, write finalists/REPORT.md.

Mirrors integrations/corr_finalize.py and lift_finalize.py. Finalists are the best
verified source of each COMPLETE live-* arm, the naive seed (control a) and the
cyclic-sweep control (b). Holdout (frozen/holdout.json: m=9 r=1..5, m=9 r=6,
m=10 r=3) is loaded only here, with allow_holdout, after a hash check against
frozen/manifest.json, and each finalist is evaluated on it exactly once. Kept out
of sort_backends.py because the live approval hash covers that file's bytes.

    python -m integrations.sort_finalize --run-dir autoresearch/sort-m9-260925
"""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
import re
import shutil
import time

from integrations.sort_backends import ROOT, TASK, _sha

# SkyDiscover 0.2.0 adaevolve/database.py parent-selection labels, verbatim. The "balanced"
# mode inserts no label. Which one appears is drawn from an unseeded RNG (random_seed unset
# in the sky config), so an AdaEvolve arm's first solution prompt can differ from the approved
# capture in exactly this block and nowhere else (GUARD-NOTE.md).
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


def _first_solution(paths, payload_of):
    from integrations.sort_backends import is_solution_request

    for path in paths:
        messages = payload_of(path).get("messages", [])
        if is_solution_request(messages):
            return path, messages
    return None, None


def admit_prompt_mismatch(camp: Path, run_dir: Path, manifest: dict, ledger_stem: str):
    """Admission record for a FIRST_PROMPT_MISMATCH arm, or (None, reason) to keep it excluded."""
    from integrations.lift_backends import messages_sha256

    engine = manifest.get("engine")
    check = manifest.get("first_solution_prompt_check") or {}
    expected_file = camp / f"first-prompt-{engine}.sha256"
    if engine not in ("adaevolve", "evox") or not expected_file.is_file():
        return None, "no approved first-prompt hash for this engine"
    expected = expected_file.read_text().split()[0]
    receipts = sorted((camp / f"{ledger_stem}.{engine}.json.receipts").glob("attempt-*.json"))
    live_path, live = _first_solution(receipts, lambda p: json.loads(p.read_text()).get("request_payload") or {})
    if live is None or messages_sha256(live) != check.get("actual_sha256"):
        return None, "live first solution request not found or not the one the guard recorded"
    captures = sorted(camp.glob(f"first-prompt-capture*/capture-{engine}-*/request-*.json"))
    captured = next((json.loads(p.read_text())["body"]["messages"] for p in captures
                     if messages_sha256(json.loads(p.read_text())["body"]["messages"]) == expected), None)
    if captured is None:
        return None, "approved captured prompt not found"
    ok, diff, reason = mode_only_difference(live, captured)
    if not ok:
        return None, reason
    return {"rule": "only SkyDiscover's parent-selection mode-guidance block differs; system message, "
                    "program and packet byte-identical (checked by sort_finalize.mode_only_difference)",
            "live_sha256": messages_sha256(live), "captured_sha256": expected,
            "live_receipt": str(live_path), "unified_diff": diff}, reason


def best_from_evaluations(run_dir: Path):
    """(source path, summary, trace) of the best evaluation record in verified/evaluations."""
    best, trace = None, []
    for res in sorted((run_dir / "verified" / "evaluations").glob("result-*.json")):
        summary = json.loads(res.read_text())["summary"]
        ordinal = int(res.stem.split("-")[1])
        trace.append({"candidate_hash": summary["candidate_hash"], "invalid": summary["invalid"],
                      "ordinal": ordinal, "combined_score": summary["combined_score"]})
        if best is None or summary["combined_score"] > best[1]["combined_score"]:
            best = (run_dir / "verified" / "evaluations" / f"candidate-{ordinal:04d}.py", summary)
    if best is None or _sha(best[0].read_bytes()) != best[1]["candidate_hash"]:
        raise SystemExit(f"abort: no verifiable best evaluation record in {run_dir}")
    return best[0], best[1], trace


ROW_KEYS = ("id", "m", "r", "d", "budget", "status", "valid", "within", "length", "excess", "slack", "word", "final")


def _utc(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _ledger_by_arm(camp: Path, stem: str):
    """Per-arm ledgers <stem>.<engine>.json (stem from broker-config.json, e.g. broker-ledger-sort-v2);
    ledgers of other stems (the stopped v1 attempt) are not counted."""
    rows = {}
    for ledger in sorted(camp.glob(stem + ".*.json")):
        parts = ledger.name[len(stem) + 1:].split(".")
        arm = parts[0] if len(parts) == 2 else "unattributed"
        state = json.loads(ledger.read_text())
        row = rows.setdefault(arm, {"attempts": 0, "usd": 0.0, "truncated": 0, "errors": 0, "ledgers": []})
        row["ledgers"].append(ledger.name)
        for a in state.get("attempts", []):
            receipt = Path(a.get("receipt_path") or "")
            finish = json.loads(receipt.read_text()).get("finish_reason") if receipt.is_file() else None
            row["attempts"] += 1
            row["usd"] += a.get("charged_usd") or 0.0
            row["truncated"] += finish in ("length", "max_tokens")
            row["errors"] += a.get("status") != "ok"
    return rows


def _proposal_stats(manifest):
    seed = manifest.get("seed_sha256")
    trace = manifest.get("evaluation_trace", [])
    by_hash = {}
    for e in trace:
        if e["candidate_hash"] != seed:
            by_hash[e["candidate_hash"]] = by_hash.get(e["candidate_hash"], True) and e["invalid"] == 0
    engine, me = manifest.get("engine"), manifest.get("mechanism_evidence", {})
    if engine == "gepa":
        accepted, how = max(0, len(me.get("candidate_sha256", [])) - 1), "GEPA candidates added to its pool"
    elif engine == "sequential":
        accepted, how = len(me.get("accepted_steps", [])), "greedy combined_score improvements"
    else:
        best, accepted = None, 0
        for e in sorted((x for x in trace if x["candidate_hash"] != seed), key=lambda x: x["ordinal"]):
            if best is None or e["combined_score"] > best:
                accepted, best = accepted + 1, e["combined_score"]
        how = "new best combined_score"
    rejected = (me.get("model_preflight_failures", 0) if engine == "gepa" else
                sum(1 for r in manifest.get("steps", []) if str(r.get("outcome", "")).startswith("invalid"))
                if engine == "sequential" else me.get("solution_diff_parse_failures", 0))
    return {"proposals_evaluated": len(by_hash), "valid_proposals": sum(by_hash.values()),
            "invalid": len(by_hash) - sum(by_hash.values()) + (rejected or 0), "accepted": accepted,
            "accepted_means": how}


def _finalize(args):
    from integrations import sort_audit
    from integrations import sort_evaluator as E
    from integrations.lift_backends import development_from_manifest

    camp = args.run_dir.resolve()
    out = (args.output or camp / "finalists").resolve()
    fm = (args.frozen_manifest or camp / "frozen" / "manifest.json").resolve()
    frozen = json.loads(fm.read_text())
    holdout = fm.parent / "holdout.json"
    if _sha(holdout.read_bytes()) != frozen["files"]["holdout.json"]:
        raise SystemExit("abort: holdout hash differs from the frozen manifest")
    development, dev_sha = development_from_manifest(fm)
    # ---- 1. finalists
    bc = json.loads((camp / "broker-config.json").read_text()) if (camp / "broker-config.json").is_file() else {}
    stem = Path(bc.get("ledger", "broker-ledger-sort-v2.json")).stem
    runs, admitted, refused = {}, {}, {}
    for d in sorted(p for p in camp.glob(args.arms_glob) if (p / "manifest.json").is_file()):
        m = json.loads((d / "manifest.json").read_text())
        if m.get("status") == "FIRST_PROMPT_MISMATCH":
            record, reason = admit_prompt_mismatch(camp, d, m, stem)
            if record is None:
                refused[d.name] = reason
                continue
            src, summary, trace = best_from_evaluations(d)
            m = dict(m, verified_best_hash=summary["candidate_hash"], evaluation_trace=trace,
                     verified_best_result={k: summary[k] for k in ("combined_score", "within_budget",
                                                                    "min_r_within_rate", "valid", "invalid",
                                                                    "timeouts", "mean_excess", "per_r")})
            record["best_evaluation_record"] = str(src)
            admitted[m["engine"]] = record
        elif m.get("status") != "COMPLETE" or not m.get("verified_best_result"):
            continue
        else:
            src = d / "verified" / "best.py"
        if _sha(src.read_bytes()) != m["verified_best_hash"]:
            raise SystemExit(f"abort: {src} does not match its manifest hash")
        res = m["verified_best_result"]
        key = (res["within_budget"], -(res["mean_excess"] if res["mean_excess"] is not None else 1e9))
        if m["engine"] not in runs or key > runs[m["engine"]][0]:
            runs[m["engine"]] = (key, d, m, src)
    finalists = [dict({"arm": e, "run_dir": str(d), "source": str(src), "source_sha256": m["verified_best_hash"],
                       "development_claim": m["verified_best_result"]},
                      **({"admitted_with_prompt_mismatch": admitted[e]} if e in admitted else {}))
                 for e, (_, d, m, src) in sorted(runs.items())]
    for arm, path in (("naive-control", args.naive), ("sweep-control", args.sweep)):
        finalists.append({"arm": arm, "run_dir": None, "source": str(path.resolve()),
                          "source_sha256": _sha(path.read_bytes()), "development_claim": None})
    frozen_set = {"finalists": [{k: f[k] for k in ("arm", "source_sha256")} for f in finalists],
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
        mpath.write_text(json.dumps(dict(frozen_set, created_utc=_utc(time.time()), details=finalists,
                                         excluded_prompt_mismatch=refused),
                                    indent=2, default=str) + "\n")
    srcs = {f["arm"]: out / "sources" / f"{f['arm']}.py" for f in finalists}
    for f in finalists:
        if _sha(srcs[f["arm"]].read_bytes()) != f["source_sha256"]:
            raise SystemExit(f"abort: frozen source copy for {f['arm']} changed")
    # ---- 2. holdout once, development re-run (rows with words kept for the audit)
    E.guard_not_holdout(development)
    sets = {"holdout": (holdout, E.load_set(holdout, allow_holdout=True)),
            "development": (development, E.load_set(development))}
    results = {}
    for name, (path, states) in sets.items():
        target = out / f"{name}-results.json"
        if target.exists():  # the holdout is evaluated exactly once; later calls reuse it
            results[name] = json.loads(target.read_text())
            if results[name]["file_sha256"] != _sha(path.read_bytes()):
                raise SystemExit(f"abort: {name} changed since its recorded evaluation")
            continue
        per_arm = {}
        for f in finalists:
            res = E.evaluate(srcs[f["arm"]], states, require_os_sandbox=not args.no_os_sandbox, jobs=args.jobs)
            per_arm[f["arm"]] = dict({k: res[k] for k in ("states", "within_budget", "within_fraction",
                                                          "min_r_within_rate", "worst_r", "valid",
                                                          "invalid", "mean_excess", "max_excess", "timeouts",
                                                          "incomplete", "combined_score", "per_r", "seconds",
                                                          "candidate_hash")},
                                     rows=[{k: r.get(k) for k in ROW_KEYS} for r in res["results"]])
        results[name] = {"set": name, "file_sha256": _sha(path.read_bytes()), "evaluated_utc": _utc(time.time()),
                         "evaluated_once": name == "holdout", "arms": per_arm}
        target.write_text(json.dumps(results[name]) + "\n")
    # ---- 3. independent audit
    tables = {(t["m"], t["r"]): (ROOT / Path(t["path"]).parent, t["table_sha256"]) for t in frozen["tables"]}
    audit = {}
    for name, (_, states) in sets.items():
        by_id = {s["id"]: s for s in states}
        audit[name] = sort_audit.audit(by_id, {a: v["rows"] for a, v in results[name]["arms"].items()}, tables)
    (out / "audit.json").write_text(json.dumps({"audit": audit}, indent=2) + "\n")
    # ---- 4. report
    manifests = {}
    for d in sorted(p for p in camp.glob(args.arms_glob) if (p / "manifest.json").is_file()):
        manifests[d.name] = json.loads((d / "manifest.json").read_text())
    ledger = _ledger_by_arm(camp, stem)
    (out / "REPORT.md").write_text(_report(finalists, runs, results, audit, ledger, frozen_set, manifests,
                                           admitted, refused))
    return {"output": str(out),
            "within": {n: {a: v["within_budget"] for a, v in results[n]["arms"].items()} for n in sets},
            "audit": {n: {a: (v["agree"], len(v["disagree"])) for a, v in d.items()} for n, d in audit.items()}}


def _fmt(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def _report(finalists, runs, results, audit, ledger, frozen_set, manifests, admitted=None, refused=None):
    hold_keys = sorted({k for v in results["holdout"]["arms"].values() for k in v["per_r"]},
                       key=lambda k: (int(k[1:k.index("r")]), int(k[k.index("r") + 1:])))
    L = [f"# sort-m9 campaign finalists ({TASK})", "",
         f"Evaluator `{frozen_set['evaluator']['version']}`. Development sha256 "
         f"`{frozen_set['development_sha256'][:16]}`, holdout sha256 `{frozen_set['holdout_sha256'][:16]}`. "
         "The holdout was evaluated once, after the finalists were frozen. A valid word is an upper bound "
         "on d(v) for that one state. Within budget means length <= T_m(n). The main conjecture remains "
         "open regardless of these results.", "",
         "## Arms", "",
         "| Arm | Calls | Valid / evaluated proposals | Invalid / truncated | Accepted | Dev within | "
         "Dev mean excess | Dev worst-r rate | Holdout within | Holdout worst-r rate | " + " | ".join(f"Holdout {k}" for k in hold_keys) +
         " | Audit disagreements (dev / holdout) | USD |",
         "|---|" + "---:|" * (11 + len(hold_keys))]
    mismatch = []
    for f in finalists:
        arm = f["arm"]
        led = ledger.get(arm, {"attempts": 0, "usd": 0.0, "truncated": 0})
        st = _proposal_stats(runs[arm][2]) if arm in runs else \
            {"proposals_evaluated": "-", "valid_proposals": "-", "accepted": "-", "invalid": "-"}
        d, h = results["development"]["arms"][arm], results["holdout"]["arms"][arm]
        claim = f.get("development_claim") or {}
        if claim and claim.get("within_budget") != d["within_budget"]:
            mismatch.append(f"{arm}: arm run claimed {claim.get('within_budget')} within budget, "
                            f"finalize re-run found {d['within_budget']}")
        L.append(f"| {arm} | {led['attempts']} | {st['valid_proposals']} / {st['proposals_evaluated']} | "
                 f"{st['invalid']} / {led['truncated']} | {st['accepted']} | {d['within_budget']}/{d['states']} | "
                 f"{_fmt(d['mean_excess'])} | {_fmt(d['min_r_within_rate'], 3)} | {h['within_budget']}/{h['states']} | "
                 f"{_fmt(h['min_r_within_rate'], 3)} | "
                 + " | ".join(f"{h['per_r'][k]['within']}/{h['per_r'][k]['states']}" if k in h['per_r'] else "-"
                              for k in hold_keys)
                 + f" | {len(audit['development'][arm]['disagree'])} / {len(audit['holdout'][arm]['disagree'])} | "
                 f"{led['usd']:.4f} |")
    L += ["", "Development re-run versus arm claims: " + ("; ".join(mismatch) if mismatch else "all agree.")]
    other = {a: v for a, v in ledger.items() if a not in {f["arm"] for f in finalists}}
    if other:
        L += ["", "Ledger attempts not tied to a finalist arm: " + "; ".join(
            f"{a}: {v['attempts']} attempts, ${v['usd']:.4f}" for a, v in sorted(other.items()))]
    L += ["", "Calls and USD come from the per-arm broker ledgers. Truncated counts responses with finish_reason "
          "length. Accepted means: GEPA candidates added to its pool, sequential greedy improvements, "
          "AdaEvolve/EvoX new best combined_score in request order.", "", "## Mechanism evidence", ""]
    for arm, (_, d, m, _) in sorted(runs.items()):
        me = m.get("mechanism_evidence", {})
        keep = {k: v for k, v in me.items() if k not in ("reflection_receipts", "candidate_sha256", "lineage")}
        if "lineage" in me:
            keep["lineage_parents"] = me["lineage"].get("parents")
        L.append(f"- **{arm}** (`{Path(d).name}`, research_status {m.get('research_status')}): "
                 f"`{json.dumps(keep, default=str)[:700]}`")
    for arm, rec in sorted((admitted or {}).items()):
        L.append(f"- **{arm}** admitted despite FIRST_PROMPT_MISMATCH: {rec['rule']}. Live "
                 f"`{rec['live_sha256'][:16]}` vs approved `{rec['captured_sha256'][:16]}`; its finalist is the best "
                 f"record in verified/evaluations (`{Path(rec['best_evaluation_record']).name}`), re-executed here. "
                 "Diff and hashes are in finalists/manifest.json.")
    for name, reason in sorted((refused or {}).items()):
        L.append(f"- `{name}` excluded, FIRST_PROMPT_MISMATCH not admitted: {reason}.")
    incomplete = [f"{n} ({m.get('engine')}: {m.get('status')})" for n, m in manifests.items()
                  if m.get("status") not in ("COMPLETE", "FIRST_PROMPT_MISMATCH")]
    if incomplete:
        L.append(f"- Runs not COMPLETE, excluded from finalists: {', '.join(incomplete)}")
    dis = [(n, a, x) for n, d in audit.items() for a, v in d.items() for x in v["disagree"]]
    L += ["", "## Independent audit", "",
          "integrations/sort_audit.py does not import sort_evaluator or sort_backends. It re-executes every "
          "returned word with its own L/R/X list executor and checks the final vector against (1..m, 0^r). "
          "For sorted words it re-checks length <= T and excess = length - d(v), with d(v) from a fresh, "
          "sha256-verified DistanceTable load that must match the frozen manifest's table hash.",
          f"Words checked: " + "; ".join(f"{n} {a} {v['checked_words']}" for n, d in audit.items()
                                         for a, v in d.items()) + ".",
          f"Disagreements: {len(dis)}."] + [f"- {n} {a} {x['id']}: {x['reason']}" for n, a, x in dis[:20]]
    hold = results["holdout"]["arms"]
    engine_arms = [a for a in runs if a != "sequential"]
    operational = any(_proposal_stats(runs[a][2])["valid_proposals"] > 0 for a in engine_arms)
    sweep_h = hold["sweep-control"]["within_budget"]
    best_arm = max(runs, key=lambda a: (hold[a]["within_budget"], -(hold[a]["mean_excess"] or 1e9)), default=None)
    best_h = hold[best_arm]["within_budget"] if best_arm else None
    full_r = sorted(k for a in runs for k, g in hold[a]["per_r"].items() if g["within"] == g["states"])
    L += ["", "## Success levels", "",
          f"- **Operational:** {'yes' if operational else 'no'}. "
          + ("At least one native engine produced valid evolving sorting programs, with the mechanism traces above."
             if operational else "No native engine produced a valid evaluated proposal."),
          "- **Mathematical:** finite only. Every audited within-budget word certifies d(v) <= T for its one "
          "sampled state. " + (f"Some finalist sorted every sampled holdout state within T for {sorted(set(full_r))}; "
                               "that is a statement about the sampled states only, not about every state of that (m, r). "
                               if full_r else "")
          + "No sorting program is proved to meet T on all states, and the main conjecture remains open.",
          f"- **Comparative:** not established. One seed, one model and one budget per arm. The best engine "
          f"finalist ({best_arm}) has {best_h} holdout states within budget, against {sweep_h} for the "
          f"cyclic-sweep control and {hold['naive-control']['within_budget']} for the naive seed, out of "
          f"{hold['sweep-control']['states']}. These differences are descriptive and do not rank the engines.",
          "", "## Limitations", "",
          "- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.",
          "- Development and holdout are finite stratified samples (300 per table, top layers oversampled). "
          "All radius states of m=9 r=1..5 are in development, so the m=9 r=1..5 holdout has no state at T.",
          "- A crash, timeout or long word proves nothing about d(v). Truncated proposals were never repaired.",
          "- The packet's best-so-far line reflects the verifier state when the packet was built.",
          "- Version 2 contract: 0.2 s CPU per state, so every finalist is a constructive program. The stopped "
          "attempt 1 (live-gepa-260925-120053, per-state search under the 2 s v1 limit) is excluded.",
          "- The (9,6) holdout uses T_9(15) = 80 while its exact radius is 79; (10,3) uses T_10(13) = 71."]
    return "\n".join(L) + "\n"


def parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True, type=Path, help="campaign directory holding the arm runs")
    ap.add_argument("--arms-glob", default="live-v2-*", help="v2 runs only; the stopped v1 attempt is live-gepa-*")
    ap.add_argument("--frozen-manifest", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--naive", type=Path, default=ROOT / "integrations" / "sort_control_naive.py")
    ap.add_argument("--sweep", type=Path, default=ROOT / "integrations" / "sort_control_sweep.py")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-os-sandbox", action="store_true", help="tests only")
    return ap


def main(argv=None):
    print(json.dumps(_finalize(parser().parse_args(argv)), default=str))


if __name__ == "__main__":
    main()
