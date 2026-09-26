"""Campaign 3 of the bound-m task (autoresearch/bound-m-c3-260926/TASK-c3.md).

Search-side only. Campaign 2's driver (bound_c2) with the tree contract:
- candidates are scored by bound-eval-3 (bound3_evaluator: tree certificates, criterion (8) per
  leaf by exact LP); a plain {"words": [...]} is one unit-origin root leaf;
- the system prompt, objective and packet (BOUND_PACKET_V3) describe trees, refined origins and
  the worst leaf (box, origins, LP lhs, slope excess, support words);
- no word pool (tree leaves on refined bases do not pool across candidates);
- the contact pool is campaign-config `contact_pool`; money is capped by the broker at max_usd
  minus the spend of the other c3 ledgers (the conservative reservation formula alone would allow
  only floor(max_usd / reservation) contacts);
- `kill-check` evaluates the s1 runs' accepted candidates on the validation set (TASK-c3.md).

Engines see only the campaign 1 development set (m = 9, 10; bound_backends.BoundVerifier refuses
any other m). The validation set (m = 11) is read only by `kill-check` and seed_eval_c3.py; the
holdout is never read here.

The staged copy runs inside the optimizer sandbox next to staged bound_c2.py, bound_backends.py,
lift_backends.py and official_backends.py, so the top level imports only those and the stdlib.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Fr
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from integrations import bound_backends as bb
    from integrations import bound_c2 as c2
    from integrations import lift_backends as lb
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import bound_backends as bb
    import bound_c2 as c2
    import lift_backends as lb
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "autoresearch" / "bound-m-c3-260926"
TASK = "bound-m-c3-260926"
PACKET_MARK = "BOUND_PACKET_V3"
PACKET_MAX = 3000
ARMS = c2.ARMS
_sha, _load = c2._sha, c2._load

SYSTEM = (
    "Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family "
    "of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two "
    "entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of k nonempty gaps "
    "(gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have u_j >= 1 zeros in "
    "the j-th gap of S; the unit base has one zero per gap. The candidate source must define certify(family) "
    "-> {'tree': NODE} (a plain {'words': [...]} is one leaf with unit origins). NODE is a split "
    "{'j': axis, 't': 1..12, 'le': NODE, 'ge': NODE} (u_j <= t goes to le, u_j >= t+1 to ge; the root box is "
    "[1, inf)^k) or a leaf {'words': [...], 'origins': [o_0..o_{k-1}], 'picks'?: [...]}: depth <= 6, <= 32 "
    "leaves, 1..32 words per leaf, <= 4000 letters per word, <= 256000 in all, o_j <= the leaf's lower corner "
    "l_j. A leaf's words are literal words on the REFINED base, where block j holds o_j zeros (picks[j], "
    "default 0, is the zero of block j that stretches); each must sort it to (1..m, 0..0) and never swap two "
    "zeros. The trusted evaluator prices each word with the research group's Lemma 1 (exact, any m): "
    "B = (number of X) + sum over segments of |net rotation|, beta_j = 2 * (X letters touching the stretched "
    "zero of block j) + sum over segments of |signed crossings of it| (a segment ends at every X), and cost "
    "C(u) = B + sum_j beta_j (u_j - o_j) on the leaf. Per leaf with box [l_j, h_j] an exact LP over your "
    "words checks criterion (8): some mixture has Cbar(l) - T(l) + sum over bounded j of "
    "max(0, betabar_j - s)(h_j - l_j) < 1 and betabar_j <= s on every unbounded axis, with s = m - 2 and "
    "T(l) = m(m+1)/2 + (sum_j l_j - 1)(m-2). The family is CERTIFIED when every leaf passes; that proves "
    "d(v) <= T_m(n) for every state of the family. Refining the stretched block (origin o_j > 1 on a leaf far "
    "out on axis j) lowers the slope a word needs there. Each family gets 3 s of CPU (module import 1 s). "
    "Score per m: percentage certified (the worst m counts twice), plus small terms for valid output and a "
    "small worst leaf gap. Development families are m = 9 and 10, reversal-type orders oversampled; the "
    "holdout has unseen families and an unseen m, so the program must work for any m with no tables: string "
    "constants over L/R/X of 24+ characters, literal containers with more than 64 elements and bytes "
    "constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. Do not read files, the network, or "
    "environment variables. Misses prove nothing."
)
OBJECTIVE = (
    "Improve this Python certify(family) program. It returns the campaign-2 lift-and-sweep word set as one "
    "unit-origin leaf when a float LP says criterion (7) holds; otherwise, axis by axis, it builds a staircase "
    "tree: at lower corner l on axis j the leaf uses origin o_j = min(l, 3), words from the same lift-and-sweep "
    "generator on the refined base priced with picks, and a float LP for criterion (8); the unbounded leaf "
    "[l, inf) closes the tree, else the widest passing [l, h] is kept and l = h + 1. Return the entire "
    "replacement Python source in one fenced code block, with no prose and no docstring longer than a few "
    "lines. Raise the number of certified families, first on the worst m: better words on refined bases "
    "(slopes beta_j at most m-2 on unbounded axes), better split axes, origins and picks, splits on two axes, "
    "and better use of the 3 s CPU. Most misses are reversal-orbit and near-reversal orders. Only development "
    "families are shown.")


# ------------------------------------------------------------------- packet v3
def leaf_lines(leaf, n_words=4) -> list:
    box = " x ".join(f"[{a},{b}]" for a, b in leaf["box"])
    lines = [f"  worst leaf {leaf['leaf']}: box {box} origins {leaf['origins']} T(l)={leaf['T']} {leaf['status']} "
             f"gap {bb._f(leaf['gap'], 3)} lhs {bb._f(leaf['lhs'], 3)} (needs < 1) slope excess "
             f"{bb._f(leaf['slope_excess'], 3)}"]
    sup = sorted(leaf["support"], key=lambda x: (-Fr(x["weight"]), x["base"]))[:n_words]
    for x in sup:
        lines.append(f"  word {x['index']} w={bb._f(x['weight'], 3)} len={len(x['word'])} B={x['base']} "
                     f"beta={x['beta']} C(l)={bb._f(x['cost_at_l'])}")
    return lines


def family_lines_v3(row, fam) -> list:
    T, s = row["budget_unit"], row["slope_bound"]
    head = (f"- {row['id']} ({row.get('class')}) m={row['m']} k={row['k']} mask={row['mask']} gaps={fam['gaps']} "
            f"unit_base={fam['unit_base']} T={T} s={s}: {row['status']} g={bb._f(row['gap'], 3)}; reversal orbit: "
            f"{'yes' if c2.reversal_orbit(fam['labels']) else 'no'}")
    t = row.get("trace", {})
    if not row["valid"]:
        fw = t.get("failed_word")
        why = (f"leaf {fw.get('leaf')} word {fw.get('index')}: {fw.get('reason')}"
               + ("; LEMMA-1 LITERAL FAILURE (evaluator alarm)" if row.get("lemma1_literal_failure") else "")
               if fw else str(t.get("failure"))[:240])
        return [head, "  " + why]
    leaves = row.get("leaves") or []
    lines = [head, f"  tree: {row.get('n_leaves')} leaves, "
             f"{sum(x['status'] == 'CERTIFIED' for x in leaves)} pass"]
    if leaves:
        worst = max(leaves, key=lambda x: (Fr(x["gap"]), -x["leaf"]))
        lines += leaf_lines(worst)
    lines.append(f"  bound: {row['bound']['statement']}")
    return lines


def packet_v3(result, fams_by_id, best_text, scope, baseline=None, hint=None) -> str:
    """Development-only feedback: totals, best so far, <= 3 failing families with their worst leaf."""
    head = [f"{PACKET_MARK} ({scope}; development only; search signal, not proof)"]
    head += bb.totals_lines(result, "this candidate")
    if scope.startswith("family"):
        r = result["results"][0]
        score = 1.0 if r["status"] == "CERTIFIED" else (0.5 / (1 + float(Fr(r["gap"]))) if r["valid"] else 0.0)
        head.append(f"this family: per-family score {score:.4f} (1 certified, 0.5/(1+g) valid miss, 0 invalid); "
                    f"best so far: {best_text}")
    else:
        head.append(f"this candidate combined {result['combined_score']:.4f}; best so far: {best_text}")
    if baseline:
        head.append(baseline)
    blocks = [family_lines_v3(r, fams_by_id[r["id"]]) for r in bb.failing(result["results"])]
    tail = [bb.MECHANISM] + list(hint or [])

    def render():
        return "\n".join(head + [ln for b in blocks for ln in b] + tail)

    text = render()
    while len(text) > PACKET_MAX:
        with_words = [b for b in blocks if any(ln.startswith("  word ") for ln in b)]
        if not with_words:
            break
        big = max(with_words, key=len)
        big.pop(max(i for i, ln in enumerate(big) if ln.startswith("  word ")))
        text = render()
    while len(text) > PACKET_MAX and blocks:
        blocks.pop()
        text = render()
    return text[:PACKET_MAX]


# ------------------------------------------------------------------- verifier
class C3Verifier(c2.C2Verifier):
    """C2Verifier scored by bound-eval-3 with packet v3 and no word pool."""

    def _admit(self, rows, digest):
        return None

    def pool_stats(self, rows) -> tuple:
        return [], {}

    def evaluate(self, source: str, family_id=None, *, final=False) -> dict:
        from integrations import bound3_evaluator as B3
        from integrations.bound_evaluator import per_example_metric

        with self.lock:
            if self.state["requests"] >= self.max_requests:
                raise PermissionError("evaluation request budget exhausted")
            self.state["requests"] += 1
            ordinal = self.state["requests"]
            path = self.evidence / f"candidate-{ordinal:04d}.py"
            path.write_text(source)
            digest = _sha(source.encode())
            if digest not in self.state["distinct_source_hashes"]:
                self.state["distinct_source_hashes"].append(digest)
            subset, scope = (([self.by_id[family_id]], "family " + family_id) if family_id
                             else (self.screen, "screen"))
            res = B3.evaluate(path, subset, jobs=self.jobs, cache_dir=self.cache_dir,
                              require_os_sandbox=self.require_os_sandbox)
            promising = False
            if family_id is None:
                prior, _ = self._current_best()
                promising = res["valid"] == res["families"] and (prior is None or res["combined_score"] >= prior["score"])
                if promising and digest not in self.state["screen_valid_source_hashes"]:
                    self.state["screen_valid_source_hashes"].append(digest)
            full = None
            if promising or final:
                full = B3.evaluate(path, self.full, jobs=self.jobs, cache_dir=self.cache_dir,
                                   require_os_sandbox=self.require_os_sandbox)
                self.state["full_evaluations"] += 1
            fsum = ({"combined_score": full["combined_score"], "certified": full["certified"],
                     "valid": full["valid"], "families": full["families"], "max_W": full["max_W"],
                     "per_m_certified": {m: g["certified"] for m, g in full["per_m"].items()},
                     "per_m": {m: {x: g[x] for x in ("certified", "families", "pct", "boundary", "invalid",
                                                    "incomplete", "timeouts", "W", "W_complete", "G", "per_k")}
                               for m, g in full["per_m"].items()},
                     "trees": sum(1 for r in full["results"] if (r.get("n_leaves") or 0) > 1),
                     "cache_key": full["cache_key"]} if full else None)
            row = {"scope": scope, "candidate_hash": digest, "combined_score": res["combined_score"],
                   "certified": res["certified"], "valid": res["valid"], "families": res["families"],
                   "cache_hit": res["cache_hit"], "full": fsum}
            bs, bf = self._current_best(extra=row)
            self.state["best_screen"], self.state["best_full"] = bs, bf
            if self.baseline is None and full:
                self.baseline = "seed full development: " + ", ".join(
                    f"m={m} {g['certified']}/{g['families']}" for m, g in full["per_m"].items())
            feedback = packet_v3(res, self.by_id, self._best_text(bs, bf), scope, self.baseline, self.hint)
            part1, part2 = bb.split_packet(feedback)
            example = per_example_metric(res["results"][0]) if family_id else None
            summary = {"combined_score": res["combined_score"], "certified": res["certified"], "valid": res["valid"],
                       "families": res["families"], "boundary": res["boundary"], "incomplete": res["incomplete"],
                       "timeouts": res["timeouts"], "max_W": res["max_W"], "max_W_float": float(Fr(res["max_W"])),
                       "scope": scope, "example_score": example, "candidate_hash": digest,
                       "cache_hit": res["cache_hit"], "evaluation_cache_key": res["cache_key"],
                       "feedback": feedback, "feedback_part1": part1, "feedback_part2": part2, "full": fsum}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "stage": res, "full": full}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row.update(ordinal=ordinal, packet_sha256=_sha(feedback.encode()))
            self.state["evaluations"].append(row)
            return summary


# ------------------------------------------------------------------- configs
def campaign(camp=CAMP):
    camp = Path(camp)
    return _load(camp / "campaign-config-c3.json"), _load(camp / "broker-config-c3.json")


def forbidden_ids(cc) -> set:
    """Validation family ids. Holdout families are m = 11, 12 and BoundVerifier refuses any m other than 9, 10,
    so the holdout file is never opened here."""
    man = _load(ROOT / cc["frozen_manifest"])
    return {f["id"] for f in _load((ROOT / cc["frozen_manifest"]).parent / "validation.json")["families"]} \
        if man.get("files", {}).get("validation.json") else set()


def pool(bc) -> int:
    return int(bc["contact_pool"])


def ledger_path(camp, bc, engine, seed) -> Path:
    return c2.ledger_path(camp, bc, engine, seed)


def spend(camp, bc, exclude=None) -> dict:
    return c2.spend(camp, bc, exclude)


def sky_config(args, stage, seed, template_dir=None) -> dict:
    config = c2.sky_config(args, stage, seed, template_dir)
    config["prompt"]["system_message"] = SYSTEM
    return config


def engine_knobs(cc, bc, engine, seed) -> dict:
    knobs = c2.engine_knobs(cc, bc, engine, seed)
    if "sky" in knobs:
        knobs["sky"]["prompt"]["system_message"] = SYSTEM
    return knobs


# ------------------------------------------------------------------- runs
def _setup(args, engine, cc):
    dev, c1_man, _ = c2.frozen_paths(cc)
    provenance = lb._verify_inputs(dev.resolve(), c1_man.resolve())
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.py"
    shutil.copyfile(ROOT / cc["seed_program"], seed)
    if _sha(seed.read_bytes()) != cc["seed_sha256"]:
        raise RuntimeError("seed program differs from campaign-config seed_sha256")
    provenance = dict(provenance, seed_sha256=_sha(seed.read_bytes()), c2_manifest_sha256=_sha(
        (ROOT / cc["frozen_manifest"]).read_bytes()))
    hint = (cc.get("hint") or {}).get("lines") if (cc.get("hint") or {}).get("enabled") else None
    verifier = C3Verifier(dev, run_dir, cache_dir=ROOT / cc["eval_cache"], engine=engine, provenance=provenance,
                          max_requests=args.max_evals, jobs=args.jobs, hint=hint, forbidden_ids=forbidden_ids(cc))
    (stage / "dataset.json").write_text(json.dumps({
        "train": [f["id"] for f in verifier.full if f["id"] not in set(verifier.screen_ids)],
        "screen": verifier.screen_ids}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


class C3BrokerLM(bb.BoundBrokerLM):
    """GEPA reflection model: bound_backends.BoundBrokerLM with the v3 packet marker in receipts."""

    def __call__(self, request):
        n = len(self.receipts)
        out = super().__call__(request)
        text = request if isinstance(request, str) else json.dumps(request)
        if len(self.receipts) > n:
            self.receipts[n]["packet_seen"] = PACKET_MARK in text
        return out


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    data = json.loads(args.dataset.read_text())
    train = [{"id": f} for f in data["train"]]
    val = [{"id": f} for f in data["screen"]]
    lm = C3BrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout, args.reasoning_effort)
    lm.receipts = []
    lm.expected_first_sha256 = args.expected_first_prompt_sha256

    def verify(source, family_id=None):
        payload = json.dumps({"source": source, "family_id": family_id}).encode()
        with urlopen(Request(args.verifier_url, payload, {"Content-Type": "application/json"}),
                     timeout=args.eval_timeout) as response:
            return json.load(response)

    def evaluator(candidate, example):
        r = verify(candidate, example["id"])
        return float(r["example_score"]), {"family_id": example["id"], "certified": r["certified"],
                                           "valid": r["valid"], "gap": r["max_W"], "feedback": r["feedback"]}

    minibatch = lb.reflection_minibatch_size(train)
    per_proposal = lb.gepa_metric_calls_per_proposal(minibatch, val)
    result = optimize_anything(
        seed_candidate=args.seed.read_text(), evaluator=evaluator, dataset=train, valset=val,
        objective=OBJECTIVE, background=SYSTEM,
        config=GEPAConfig(
            engine=EngineConfig(run_dir=str(args.run_dir / "gepa"), seed=args.gepa_seed,
                                max_candidate_proposals=args.proposals,
                                max_metric_calls=len(val) + (args.proposals + 1) * per_proposal,
                                max_workers=1, parallel=False),
            reflection=ReflectionConfig(reflection_lm=lm, reflection_minibatch_size=minibatch)))
    best = result.best_candidate
    if not isinstance(best, str):
        raise TypeError("GEPA returned a non-source candidate")
    (args.run_dir / "best.py").write_text(best)
    full = verify(best)
    lineage = {k: getattr(result, k, None) for k in ("parents", "val_aggregate_scores", "discovery_eval_counts",
                                                     "total_metric_calls", "num_full_val_evals")}
    candidates = [c if isinstance(c, str) else json.dumps(c) for c in getattr(result, "candidates", [])]
    summary = {"engine": "gepa", "gepa_seed": args.gepa_seed, "upstream": ob.UPSTREAM["gepa"],
               "best_path": str(args.run_dir / "best.py"), "best_screen_score": full["combined_score"],
               "best_idx": getattr(result, "best_idx", None),
               "candidate_sha256": [_sha(c.encode()) for c in candidates], "lineage": lineage,
               "reflection_calls": lm.calls, "model_valid_responses": lm.valid_responses,
               "model_preflight_failures": lm.preflight_failures, "reflection_receipts": lm.receipts,
               "minibatch": minibatch, "metric_calls_per_proposal": per_proposal, "final_request": full}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _launch(args, cc) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    args.broker_url = ob._broker_url(args.broker_url)
    python = args.python.absolute()
    upstream = ob._installed_identity(python, args.engine)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, args.engine, cc)
    for mod in (ob, lb, bb, c2):
        shutil.copyfile(Path(mod.__file__), stage / Path(mod.__file__).name)
    shutil.copyfile(Path(__file__), stage / "bound_c3_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "bound_c3_worker.py"), "_gepa_worker",
                   "--seed", str(seed), "--dataset", str(stage / "dataset.json"),
                   "--run-dir", str(run_dir / "output"), "--broker-url", args.broker_url,
                   "--model", args.model, "--verifier-url", verifier_url,
                   "--max-tokens", str(args.max_tokens), "--proposals", str(args.iterations),
                   "--llm-timeout", str(args.llm_timeout), "--eval-timeout", str(args.eval_timeout),
                   "--gepa-seed", str(args.run_seed)]
        if args.expected_first_prompt_sha256:
            command += ["--expected-first-prompt-sha256", args.expected_first_prompt_sha256]
        if args.reasoning_effort:
            command += ["--reasoning-effort", args.reasoning_effort]
    else:
        config = stage / "sky-config.yaml"  # JSON is valid YAML
        config.write_text(json.dumps(sky_config(args, stage, args.run_seed), indent=2) + "\n")
        evaluator = bb._sky_evaluator(stage, verifier_url, args.eval_timeout)
        command = [str(python), "-m", "skydiscover", "optimize", str(seed), str(evaluator),
                   "--config", str(config), "--search", args.engine, "--iterations", str(args.iterations),
                   "--output", str(run_dir / "output" / "sky"), "--log-level", "INFO"]
    base_python = Path(os.path.realpath(python))
    read_paths = ["/System", "/usr", "/Library", "/opt/homebrew", "/private/etc", "/dev",
                  str(python.parent.parent), str(base_python.parent.parent), str(stage)]
    profile = run_dir / "worker.sb"
    profile.write_text(sandbox_profile(read_paths=read_paths, write_paths=[run_dir / "output"],
                                       loopback_ports=[urlparse(args.broker_url).port, urlparse(verifier_url).port],
                                       allow_python_multiprocessing=True))
    wrapped = sandbox_command(command, profile)
    manifest = {"engine": args.engine, "seed": args.run_seed, "task": TASK, "upstream": upstream, **provenance,
                "seed_full": seed_eval["full"], "broker_url": args.broker_url, "model": args.model,
                "iterations": args.iterations, "max_tokens": args.max_tokens,
                "reasoning_effort": args.reasoning_effort, "max_evals": args.max_evals,
                "wall_seconds": args.wall_seconds, "verifier_url": verifier_url, "command": command,
                "sandbox_command": wrapped, "sandbox_profile": str(profile), "run_dir": str(run_dir),
                "sky_random_seed": args.run_seed if args.engine != "gepa" else None,
                "gepa_seed": args.run_seed if args.engine == "gepa" else None,
                "evox_strategy_evolution": False if args.engine == "evox" else None}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    start = time.monotonic()
    try:
        with (run_dir / "console.log").open("w") as log:
            proc = subprocess.Popen(wrapped, cwd=run_dir / "output", env=env, stdout=log,
                                    stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                returncode = proc.wait(timeout=args.wall_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                returncode = proc.returncode
                manifest["reason"] = "official optimizer wall time limit"
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    finally:
        server.shutdown()
        server.server_close()
    manifest["returncode"] = returncode
    manifest["engine_seconds"] = time.monotonic() - start
    manifest["mechanism_evidence"] = ob._mechanism_evidence(run_dir, args.engine, args.iterations, args.ledger)
    if args.engine == "gepa" and (run_dir / "output" / "summary.json").is_file():
        s = _load(run_dir / "output" / "summary.json")
        manifest["mechanism_evidence"].update({k: s[k] for k in ("lineage", "best_idx", "candidate_sha256",
                                                                 "reflection_receipts", "minibatch",
                                                                 "metric_calls_per_proposal")})
    if args.engine in ("adaevolve", "evox"):
        check = bb.verify_first_solution_prompt(args.ledger, args.expected_first_prompt_sha256)
        manifest["first_solution_prompt_check"] = (None if check is None else
                                                   {"actual_sha256": check[0], "matches": check[1]})
        if check is not None and not check[1]:
            manifest["status"] = manifest["research_status"] = "FIRST_PROMPT_MISMATCH"
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
            raise RuntimeError("first solution prompt differs from the approved first-prompt hash")
    if returncode:
        console = (run_dir / "console.log").read_text(errors="replace")
        manifest["status"] = manifest["research_status"] = (
            "FIRST_PROMPT_MISMATCH" if "first proposer prompt differs" in console else "INCOMPLETE")
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        raise RuntimeError(f"official {args.engine} exited {returncode}; see {run_dir / 'console.log'}")
    best = (run_dir / "output" / "best.py" if args.engine == "gepa"
            else run_dir / "output" / "sky" / "best" / "best_program.py")
    trusted_best = ob._snapshot_best(best, run_dir / "output", run_dir / "verified")
    manifest["status"] = "COMPLETE"
    return bb._finish(manifest, run_dir, verifier, seed_eval, trusted_best.read_text())


def _sequential(args, cc) -> dict:
    """Control arm: same broker, system prompt and packet; greedy accept on the screen combined_score."""
    args.broker_url = ob._broker_url(args.broker_url)
    run_dir, stage, seed, verifier, provenance, seed_eval = _setup(args, "sequential", cc)
    best_source, best = seed.read_text(), seed_eval
    trace, history, last = [], [], None
    manifest = {"engine": "sequential", "seed": args.run_seed, "task": TASK, **provenance,
                "broker_url": args.broker_url, "model": args.model, "iterations": args.iterations,
                "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort, "max_evals": args.max_evals,
                "run_dir": str(run_dir), "provider_seed": None}
    status = "COMPLETE"
    for step in range(1, args.iterations + 1):
        user = (OBJECTIVE + "\n\n" + lb.rejection_note(history) + "Current program:\n```python\n" + best_source
                + "\n```\n\n" + "Evaluator feedback:\n" + best["feedback"]
                + "\n\nProvide ONLY the complete new program within ```python ... ``` blocks.")
        request_sha256 = _sha(user.encode())
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        row = {"step": step, "packet_seen": PACKET_MARK in user, "request_sha256": request_sha256}
        if step == 1 and bb.first_prompt_mismatch(messages, args.expected_first_prompt_sha256):
            row["outcome"] = "guard: first prompt differs from the approved first-prompt hash"
            trace.append(row)
            status = "FIRST_PROMPT_MISMATCH"
            break
        if request_sha256 == last:
            row["outcome"] = "guard: refusing to resend an identical consecutive prompt"
            trace.append(row)
            status = "GUARD_STOPPED"
            break
        last = request_sha256
        try:
            content, finish = lb._chat(args.broker_url, args.model, args.max_tokens, args.reasoning_effort,
                                       messages, args.llm_timeout)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            row["outcome"] = f"broker stopped: {exc}"
            trace.append(row)
            status = "BROKER_STOPPED"
            break
        row["finish_reason"] = finish
        try:
            source = bb.preflight_source(content, finish)
        except (SyntaxError, ValueError) as exc:
            row["outcome"] = reason = f"invalid proposal: {exc}"
            history.append({"step": step, "reason": reason})
            trace.append(row)
            continue
        try:
            result = verifier.evaluate(source)
        except PermissionError as exc:
            row["outcome"] = str(exc)
            trace.append(row)
            status = "EVAL_BUDGET"
            break
        accepted = result["combined_score"] > best["combined_score"]
        row.update({"candidate_hash": result["candidate_hash"], "score": result["combined_score"],
                    "certified": result["certified"], "accepted": accepted})
        if accepted:
            best_source, best = source, result
        else:
            row["outcome"] = reason = (f"rejected: screen combined {result['combined_score']:.4f} (certified "
                                       f"{result['certified']}, valid {result['valid']}/{result['families']}) did not "
                                       f"beat {best['combined_score']:.4f}")
            history.append({"step": step, "reason": reason})
        trace.append(row)
    (run_dir / "sequential-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    (run_dir / "verified").mkdir(exist_ok=True)
    (run_dir / "verified" / "best.py").write_text(best_source)
    manifest.update({"status": status, "steps": trace,
                     "mechanism_evidence": {"accepted_steps": [r["step"] for r in trace if r.get("accepted")],
                                            "accepted_hashes": [r["candidate_hash"] for r in trace if r.get("accepted")],
                                            "packet_seen_steps": [r["step"] for r in trace if r["packet_seen"]],
                                            "truncated_steps": [r["step"] for r in trace if r.get("finish_reason")
                                                                in ("length", "max_tokens")]}})
    if status == "FIRST_PROMPT_MISMATCH":
        manifest["research_status"] = status
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        return manifest
    return bb._finish(manifest, run_dir, verifier, seed_eval, best_source)


def run(args) -> dict:
    cc, _ = campaign(args.campaign_dir)
    return _sequential(args, cc) if args.engine == "sequential" else _launch(args, cc)


# ------------------------------------------------------------------- first prompts
def first_prompt_file(camp, engine, seed) -> Path:
    return Path(camp) / "first-prompts" / f"first-prompt-{engine}-s{seed}.sha256"


def write_first_prompt(capture_dir, engine, seed, camp=CAMP) -> str:
    path, body = c2.captured_first(capture_dir, engine)
    messages = body["messages"]
    digest = lb.messages_sha256(messages)
    target = first_prompt_file(camp, engine, seed)
    target.parent.mkdir(exist_ok=True)
    fence = "`" * 6
    when = ("A live run halts before its first model request if these messages hash differently."
            if engine in ("gepa", "sequential") else
            "A live run is marked FIRST_PROMPT_MISMATCH and fails if its first solution request in the run's ledger "
            "receipts hashes differently (SkyDiscover has no pre-send hook).")
    lines = [f"# First {engine} proposer prompt, seed {seed} ({TASK})", "",
             "Captured offline through the mock (no provider call). Only development families (m = 9, 10) appear; "
             "the validation (m = 11) and holdout (m = 11, 12) sets are never loaded by an engine.", "",
             f"- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `{digest}`",
             f"- Message roles: {[m['role'] for m in messages]}",
             f"- Client request fields: model `{body.get('model')}`, max_tokens `{body.get('max_tokens')}`, "
             f"reasoning_effort `{body.get('reasoning_effort')}`",
             f"- Captured from: `{Path(capture_dir).name}/{path.name}`", f"- {when}", ""]
    for i, m in enumerate(messages, 1):
        lines += [f"## Message {i}: {m['role']}", "", fence + "text", m["content"], fence, ""]
    target.with_suffix(".md").write_text("\n".join(lines))
    target.write_text(f"{digest}  first {engine} s{seed} proposer request (canonical JSON of messages)\n")
    return digest


# ------------------------------------------------------------------- approval
def approval_material(camp=CAMP) -> dict:
    from integrations.bound3_evaluator import CONTRACT, VERSION, evaluator_hash
    from integrations.research_budget import _dry_run_payload

    camp = Path(camp)
    cc, bc = campaign(camp)
    dev, c1_man, man_path = c2.frozen_paths(cc)
    man = _load(man_path)
    knobs, prompts = {}, {}
    for engine in ARMS:
        for seed in cc["seeds"]:
            knobs[f"{engine}/s{seed}"] = engine_knobs(cc, bc, engine, seed)
            prompts[f"{engine}/s{seed}"] = c2._read_hash(first_prompt_file(camp, engine, seed))
    code = {n: _sha(Path(f).read_bytes()) for n, f in (("bound_c3", __file__), ("bound_c2", c2.__file__),
                                                        ("bound_backends", bb.__file__),
                                                        ("lift_backends", lb.__file__),
                                                        ("official_backends", ob.__file__))}
    for n in ("research_budget", "program_sandbox"):
        code[n] = _sha((ROOT / "integrations" / f"{n}.py").read_bytes())
    return {"campaign_config": cc, "broker_config": bc, "pool": pool(bc), "engine_knobs": knobs,
            "first_prompts": prompts,
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc),
            "prompts": {"system": SYSTEM, "objective": OBJECTIVE, "mechanism": bb.MECHANISM, "hint": cc.get("hint")},
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "artifact_max": bb.ARTIFACT_MAX,
                              "scope": "development only", "failing_families": 3,
                              "per_family": ["class and reversal orbit", "tree leaves passing",
                                             "worst leaf box, origins, T(l), lhs, slope excess", "support words"]},
            "data": {"seed_sha256": _sha((ROOT / cc["seed_program"]).read_bytes()),
                     "c2_manifest_sha256": _sha(man_path.read_bytes()), "c2_files": man["files"],
                     "development_sha256": _sha(dev.read_bytes()), "c1_manifest_sha256": _sha(c1_man.read_bytes())},
            "evaluator": {"version": VERSION, "contract": CONTRACT, "hash": evaluator_hash()},
            "code_sha256": code}


def approval_hash(camp=CAMP) -> str:
    return _sha(lb._canonical(approval_material(camp)).encode())


def check_approval(camp=CAMP) -> str:
    camp = Path(camp)
    computed = approval_hash(camp)
    approved = camp / "payload-approved.sha256"
    if not approved.is_file():
        raise SystemExit(f"refusing to start: {approved} is missing (created only after user approval)")
    token = approved.read_text().split()
    if not token or token[0] != computed:
        raise SystemExit(f"refusing to start: payload hash {computed} does not match {approved}")
    return computed


# ------------------------------------------------------------------- kill rule
def kill_check(camp=CAMP, seed=1, first=15, jobs=8) -> dict:
    """TASK-c3.md kill rule. For each arm's seed-`seed` live run, the accepted candidates among its first
    `first` distinct proposals (sources with a full development evaluation, in order of first appearance)
    are evaluated on the validation set (sandboxed); stop = no arm has one that certifies more validation
    families than the seed."""
    from integrations import bound3_evaluator as B3
    from integrations.bound_task import check_family

    camp = Path(camp)
    cc, _ = campaign(camp)
    man_path = ROOT / cc["frozen_manifest"]
    val_path = man_path.parent / "validation.json"
    if _sha(val_path.read_bytes()) != _load(man_path)["files"]["validation.json"]:
        raise SystemExit("validation set differs from the c2 manifest")
    fams = _load(val_path)["families"]
    for f in fams:
        check_family(f)
    seed_val = B3.evaluate(ROOT / cc["seed_program"], fams, jobs=jobs, cache_dir=ROOT / cc["eval_cache"])["certified"]
    out = {"seed_validation_certified": seed_val, "first_proposals": first, "arms": {}}
    for arm in ARMS:
        runs = sorted(camp.glob(f"live-{arm}-s{seed}-*/manifest.json"))
        if not runs:
            out["arms"][arm] = {"run": None}
            continue
        m = _load(runs[-1])
        seed_hash = m.get("seed_sha256")
        order = [r["candidate_hash"] for r in m.get("evaluation_trace", []) if r["candidate_hash"] != seed_hash]
        distinct = list(dict.fromkeys(order))[:first]
        accepted = {r["candidate_hash"]: r["ordinal"] for r in m.get("evaluation_trace", []) if r.get("full")}
        best = None
        for h in distinct:
            if h not in accepted:
                continue
            src = runs[-1].parent / "verified" / "evaluations" / f"candidate-{accepted[h]:04d}.py"
            res = B3.evaluate(src, fams, jobs=jobs, cache_dir=ROOT / cc["eval_cache"])
            if best is None or res["certified"] > best["certified"]:
                best = {"candidate_hash": h, "certified": res["certified"], "max_W": res["max_W"]}
        out["arms"][arm] = {"run": str(runs[-1].parent.resolve().relative_to(ROOT.resolve())), "status": m.get("status"),
                            "accepted_in_window": sum(h in accepted for h in distinct), "best": best,
                            "beats_seed": bool(best and best["certified"] > seed_val)}
    out["stop"] = not any(a.get("beats_seed") for a in out["arms"].values())
    return out


# ------------------------------------------------------------------- live
def budget_for(camp, cc, bc, engine, seed) -> dict:
    """Contacts and USD this (arm, seed) run may use; refuses when the pool or its sub-cap is spent."""
    ledger = ledger_path(camp, bc, engine, seed)
    other = spend(camp, bc, exclude=ledger)
    sub_cap = int(cc["engines"][engine]["max_requests"])
    contacts = min(sub_cap, pool(bc) - other["contacts"])
    usd = round(bc["max_usd"] - other["charged_usd"], 6)
    return {"ledger": ledger, "sub_cap": sub_cap, "contacts": max(0, contacts), "max_usd": usd, "other": other}


def _live(args):
    camp = Path(args.campaign_dir)
    cc, bc = campaign(camp)
    if args.seed not in cc["seeds"]:
        raise SystemExit(f"refusing: seed {args.seed} is not in campaign-config seeds")
    if not os.environ.get(bc["api_key_env"]):
        raise SystemExit("provider key must be supplied through the environment")
    digest = check_approval(camp)
    b = budget_for(camp, cc, bc, args.engine, args.seed)
    if b["contacts"] <= 0 or b["max_usd"] < bc["reservation_usd_per_request_conservative"]:
        raise SystemExit(f"refusing: no contacts or USD left for {args.engine} s{args.seed}: {b}")
    stamp = time.strftime("%y%m%d-%H%M%S")
    tag = f"{args.engine}-s{args.seed}"
    run_dir = camp / f"live-{tag}-{stamp}"
    broker_log = camp / f"broker-{tag}-{stamp}.log"
    if run_dir.exists() or broker_log.exists() or b["ledger"].exists():
        raise SystemExit("fresh run, ledger or broker log path already exists")
    port = cc["broker_port"]
    cmd = [sys.executable, "-m", "integrations.research_budget", "serve",
           "--upstream-url", bc["upstream_url"], "--model", bc["model"], "--api-key-env", bc["api_key_env"],
           "--ledger", str(b["ledger"]), "--max-requests", str(b["contacts"]), "--max-usd", str(b["max_usd"]),
           "--input-usd-per-million", str(bc["input_usd_per_million"]),
           "--output-usd-per-million", str(bc["output_usd_per_million"]), "--port", str(port),
           "--max-tokens", str(bc["max_tokens"]), "--reasoning-reserve", str(bc["reasoning_cap_tokens"]),
           "--reasoning-effort", bc["reasoning_effort"], "--reasoning-cap-tokens", str(bc["reasoning_cap_tokens"]),
           "--timeout", str(bc["timeout"])] + (["--upstream-stream"] if bc.get("upstream_stream") else [])
    with broker_log.open("w") as log:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise SystemExit("local research broker did not become ready")
        arm = cc["engines"][args.engine]
        argv = ["run", "--engine", args.engine, "--seed", str(args.seed), "--run-dir", str(run_dir),
                "--campaign-dir", str(camp), "--broker-url", f"http://127.0.0.1:{port}/v1", "--model", bc["model"],
                "--max-tokens", str(bc["max_tokens"]), "--reasoning-effort", bc["reasoning_effort"],
                "--iterations", str(min(c2.effective_iterations(cc, args.engine), b["contacts"])),
                "--max-evals", str(arm["max_evals"]), "--wall-seconds", str(arm["wall_seconds"]),
                "--llm-timeout", str(int(bc["timeout"]) + 30), "--eval-timeout", str(cc["eval_timeout"]),
                "--python", str(ROOT / cc["python"]), "--ledger", str(b["ledger"])]
        expected = c2._read_hash(first_prompt_file(camp, args.engine, args.seed))
        if expected:
            argv += ["--expected-first-prompt-sha256", expected]
        out = run(_parser().parse_args(argv))
        out.update(approved_payload_sha256=digest, ledger=str(b["ledger"].relative_to(ROOT)),
                   contacts_allowed=b["contacts"], usd_allowed=b["max_usd"])
        (run_dir / "manifest.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
        return out
    finally:
        proc.terminate()
        proc.wait()


# ------------------------------------------------------------------- CLI
def _parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("run", help="one (arm, seed) run (offline smokes through the mock; live uses `live`)")
    p.add_argument("--engine", required=True, choices=ARMS)
    p.add_argument("--seed", dest="run_seed", required=True, type=int)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--campaign-dir", type=Path, default=CAMP)
    p.add_argument("--python", type=Path, default=ROOT / ".venv-official" / "bin" / "python")
    p.add_argument("--broker-url", required=True)
    p.add_argument("--model", default="gemini-3.8-flash")
    p.add_argument("--iterations", type=int, default=2)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
    p.add_argument("--max-evals", type=int, default=400)
    p.add_argument("--wall-seconds", type=int, default=3600)
    p.add_argument("--llm-timeout", type=int, default=240)
    p.add_argument("--eval-timeout", type=int, default=900)
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--ledger", type=Path, help="this run's broker ledger (Sky first-prompt check, EvoX evidence)")
    p.add_argument("--expected-first-prompt-sha256")
    w = sub.add_parser("_gepa_worker")
    for flag in ("seed", "dataset", "run-dir"):
        w.add_argument("--" + flag, required=True, type=Path)
    for flag in ("broker-url", "verifier-url", "model"):
        w.add_argument("--" + flag, required=True)
    for flag in ("max-tokens", "proposals", "llm-timeout", "eval-timeout", "gepa-seed"):
        w.add_argument("--" + flag, required=True, type=int)
    w.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
    w.add_argument("--expected-first-prompt-sha256")
    fp = sub.add_parser("first-prompt")
    fp.add_argument("--capture-dir", required=True, type=Path)
    fp.add_argument("--engine", required=True, choices=ARMS)
    fp.add_argument("--seed", required=True, type=int)
    fp.add_argument("--campaign-dir", type=Path, default=CAMP)
    fp.add_argument("--write", action="store_true", help="write first-prompts/first-prompt-<engine>-s<seed>.{md,sha256}")
    for name in ("approval-hash", "check-approval", "campaign-spend", "live", "kill-check"):
        a = sub.add_parser(name)
        a.add_argument("--campaign-dir", type=Path, default=CAMP)
        if name == "approval-hash":
            a.add_argument("--write-material", type=Path)
        if name == "live":
            a.add_argument("--engine", required=True, choices=ARMS)
            a.add_argument("--seed", required=True, type=int)
        if name == "kill-check":
            a.add_argument("--seed", type=int, default=1)
            a.add_argument("--first", type=int, default=15)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.action == "approval-hash":
        if args.write_material:
            args.write_material.write_text(json.dumps(approval_material(args.campaign_dir), indent=2,
                                                      sort_keys=True, default=str) + "\n")
        print(approval_hash(args.campaign_dir))
        return
    if args.action == "check-approval":
        print(check_approval(args.campaign_dir))
        return
    if args.action == "campaign-spend":
        cc, bc = campaign(args.campaign_dir)
        print(json.dumps(dict(spend(args.campaign_dir, bc), pool=pool(bc), max_usd=bc["max_usd"])))
        return
    if args.action == "kill-check":
        out = kill_check(args.campaign_dir, args.seed, args.first)
        print(json.dumps(out, indent=1))
        raise SystemExit(3 if out["stop"] else 0)
    if args.action == "first-prompt":
        if args.write:
            print(write_first_prompt(args.capture_dir, args.engine, args.seed, args.campaign_dir))
        else:
            print(lb.messages_sha256(c2.captured_first(args.capture_dir, args.engine)[1]["messages"]))
        return
    if args.action == "_gepa_worker":
        return _gepa_worker(args)
    result = run(args) if args.action == "run" else _live(args)
    keep = ("engine", "seed", "status", "research_status", "run_dir", "seed_full", "verified_best_full")
    print(json.dumps({k: result.get(k) for k in keep}, default=str))


if __name__ == "__main__":
    main()
