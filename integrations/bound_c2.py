"""Campaign 2 of the bound-m task (autoresearch/bound-m-c2-260925/TASK-c2.md).

Search-side only. A new module, so the campaign 1 approval material (which hashes
bound_backends.py) stays reproducible. It reuses bound_backends (preflight, broker
client, SkyDiscover config and evaluator stub, _finish), lift_backends and
official_backends, and adds:
- three seeds per arm: SkyDiscover search.database.random_seed and GEPA EngineConfig.seed
  are the run seed (the sequential control records it; the provider gets no seed);
- per-(arm, seed) ledgers broker-ledger-bound-c2.<arm>-s<seed>.json with sub-caps from a
  shared contact pool, and a USD cap equal to max_usd minus spend in the other c2 ledgers;
- packet v2 (BOUND_PACKET_V2): the v1 content plus the order class of each failing family
  and, for reversal-orbit failures, the binding constraint at the gap-LP optimum (base or
  which slope) and the best returned word's crossing profile (A_j, rotation passes, beta_j);
  an optional 3-line hint fixed in campaign-config.json (reversal_hint);
- per-(arm, seed) first-prompt files, guards and approval material.

The development set is campaign 1's frozen development.json (by reference and hash). The
validation set (c1 holdout m = 11) and the c2 holdout (m = 12 and fresh m = 11) are never
loaded here; only integrations/bound_c2_finalize.py reads them.

The staged copy runs inside the optimizer sandbox next to staged bound_backends.py,
lift_backends.py and official_backends.py, so the module top level imports only the
standard library and those files.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Fr
import hashlib
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
    from integrations import lift_backends as lb
    from integrations import official_backends as ob
except ImportError:  # staged copy inside the optimizer sandbox
    import bound_backends as bb
    import lift_backends as lb
    import official_backends as ob

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "autoresearch" / "bound-m-c2-260925"
TASK = "bound-m-c2-260925"
PACKET_MARK = "BOUND_PACKET_V2"
PACKET_MAX = 3000
ARMS = ("gepa", "sequential", "adaevolve", "evox")
SYSTEM = bb.SYSTEM
OBJECTIVE = (
    "Improve this Python certify(family) program. The seed builds a pool of lift-and-sweep sorting words: every "
    "target rotation t, every zero routing (all k! permutations of the zeros onto the zero slots for k <= 4, the 2k "
    "dihedral ones for k >= 5) and four cursor sweeps (L, R, greedy, greedy_R); it prices each word by the Lemma 1 "
    "cost and returns the union of per-coordinate best words, Frank-Wolfe-like picks, random scalarizations and "
    "fill-ups, cut to 32. Return the entire replacement Python source in one fenced code block, with no prose and no "
    "docstring longer than a few lines. Raise the number of certified families, first on the worst m, by "
    "constructing words whose slopes beta_j stay at most m-2 (fewer labels crossing each zero block, fewer rotation "
    "passes across it) and by choosing the returned word set well. Most misses are reversal-orbit and near-reversal "
    "orders. Only development families are shown.")
FAILED = ("FIRST_PROMPT_MISMATCH", "INCOMPLETE", "REFUSED")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text())


# ------------------------------------------------------------------- packet v2
def reversal_orbit(labels) -> bool:
    """True when the label order is a cyclic rotation of m..1 (rev_rot, refl and 6 of 7 c1 tight families)."""
    m = len(labels)
    rev = list(range(m, 0, -1))
    return any(list(labels) == rev[s:] + rev[:s] for s in range(m))


def binding(row) -> str:
    """Which constraint binds at the gap-LP optimum: base (Bbar vs T+1) and/or which slopes exceed s."""
    lp = row.get("gap_lp") or row["lp"]
    base_ex = Fr(lp["base"]) - (row["budget_unit"] + 1)
    slopes = sorted(row.get("trace", {}).get("slopes") or [], key=lambda x: (-Fr(x["excess"]), x["j"]))
    over = [f"slope j={x['j']} (gap {x['gap_index']}) +{bb._f(x['excess'])}" for x in slopes if Fr(x["excess"]) > 0]
    parts = ([f"base Bbar-(T+1)=+{bb._f(base_ex)}"] if base_ex > 0 else []) + over
    if not parts:
        return "none strictly (BOUNDARY: best mixture reaches Bbar = T+1 exactly)"
    if base_ex == 0:
        parts.append("base pinned at T+1")
    return "; ".join(parts)


def best_word(row) -> int | None:
    """Index of the returned word with the smallest single-word gap (base excess + worst slope excess)."""
    words, T, s = row.get("words") or [], row["budget_unit"], row["slope_bound"]
    if not words:
        return None
    return min(range(len(words)), key=lambda i: (max(0, words[i]["base"] - (T + 1)) + max(0, max(words[i]["beta"],
                                                 default=0) - s), words[i]["base"], i))


def family_lines_v2(row, fam) -> list:
    lines = bb.family_lines(row, fam)
    orbit = reversal_orbit(fam["labels"])
    extra = [f"  order class: {row.get('class')}; reversal orbit: {'yes' if orbit else 'no'}"]
    if orbit and row["valid"] and row["status"] != "CERTIFIED":
        extra.append(f"  binding at gap-LP optimum: {binding(row)}")
        i = best_word(row)
        if i is not None:
            w, s = row["words"][i], row["slope_bound"]
            extra.append(f"  best single word {i}: B={w['base']} (T+1={row['budget_unit'] + 1}) crossing profile "
                         f"A={w['A']} rot passes={w['rotation_passes']} beta={w['beta']} vs s={s}")
    return lines[:1] + extra + lines[1:]


def packet_v2(result, fams_by_id, best_text, scope, baseline=None, hint=None, pool=None) -> str:
    """Development-only feedback: v1 content, order classes, reversal-orbit binding and crossing profiles."""
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
    head += list(pool or [])
    blocks = [family_lines_v2(r, fams_by_id[r["id"]]) for r in bb.failing(result["results"])]
    tail = [bb.MECHANISM] + list(hint or [])

    def render():
        return "\n".join(head + [ln for b in blocks for ln in b] + tail)

    text = render()
    while len(text) > PACKET_MAX:
        with_words = [b for b in blocks if any(ln.startswith("  word ") for ln in b)]
        if not with_words:
            break
        big = max(with_words, key=len)
        big.pop(max(i for i, ln in enumerate(big) if ln.startswith("  word ")))  # lowest-weight word line first
        text = render()
    while len(text) > PACKET_MAX and blocks:
        blocks.pop()
        text = render()
    return text[:PACKET_MAX]


# ------------------------------------------------------------------- word pool
def _dominates(a, b) -> bool:
    return a["B"] <= b["B"] and all(x <= y for x, y in zip(a["beta"], b["beta"]))


class WordPool:
    """Per-family development word pool: Lemma 1 costs of valid words from accepted candidates.

    Words enter only from rows the trusted evaluator already validated (Profile, literal lift), for
    development families only. Dominated cost vectors (B and every beta_j no smaller) are pruned: they
    can never lower an LP optimum. Pooled status is bound_evaluator.classify on pool (+ candidate) costs.
    A pooled certificate is a real bound for its family but not a uniform program; it is a search signal."""

    def __init__(self, path, fams_by_id, forbidden=()):
        self.path, self.fams, self.forbidden = Path(path), fams_by_id, set(forbidden)
        self.entries, self._status = {}, {}

    def _check(self, fid):
        if fid in self.forbidden or fid not in self.fams:
            raise ValueError(f"word pool accepts development families only, not {fid}")

    def costs(self, fid):
        return [(e["B"], e["beta"]) for e in self.entries.get(fid, [])]

    def classify(self, fid, costs):
        from integrations.bound_evaluator import classify
        f = self.fams[fid]
        return classify(costs, f["k"], f["slope_bound"], f["budget_unit"], f["m"], f["gaps"])

    def certified(self, fid) -> bool:
        if fid not in self._status:
            self._status[fid] = bool(self.entries.get(fid)) and \
                self.classify(fid, self.costs(fid))["status"] == "CERTIFIED"
        return self._status[fid]

    def add(self, row, source) -> bool:
        self._check(row["id"])
        if not row.get("valid") or not row.get("output_words"):
            return False
        cur, changed = self.entries.setdefault(row["id"], []), False
        for w, word in zip(row["words"], row["output_words"]):
            e = {"B": w["base"], "beta": list(w["beta"]), "word": word, "source": source[:12]}
            if any(_dominates(x, e) for x in cur):
                continue
            cur[:] = [x for x in cur if not _dominates(e, x)] + [e]
            changed = True
        if changed:
            self._status.pop(row["id"], None)
        return changed

    def gain(self, row) -> dict:
        """Pool alone vs pool + this row's words, and (when newly certified) the support split."""
        self._check(row["id"])
        pool = self.certified(row["id"])
        alone = row["status"] == "CERTIFIED"
        if pool or alone or not row.get("valid"):
            return {"id": row["id"], "pool": pool, "alone": alone, "pooled": pool or alone}
        mine = self.costs(row["id"])
        out = self.classify(row["id"], mine + [(w["base"], w["beta"]) for w in row["words"]])
        g = {"id": row["id"], "pool": False, "alone": False, "pooled": out["status"] == "CERTIFIED"}
        if g["pooled"]:
            idx, n = out["certificate"]["indices"], len(mine)
            ents = self.entries[row["id"]]
            g["yours"] = [i - n for i in idx if i >= n]
            g["others"] = [{k: ents[i][k] for k in ("B", "beta", "source")} for i in idx if i < n]
        return g

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"schema": "bound-c2-word-pool-v1", "scope": "development only",
                                   "families": self.entries}) + "\n")
        tmp.replace(self.path)

    def summary(self) -> dict:
        ids = sorted(f for f in self.entries if self.certified(f))
        return {"families": len(self.entries), "words": sum(len(v) for v in self.entries.values()),
                "certified": len(ids), "certified_ids": ids}


def pool_lines(gains, fams_by_id, n=3, empty=False) -> list:
    if not gains:
        return []
    if empty:
        return ["POOL: empty so far (valid words of accepted candidates enter after their evaluation; development "
                "only). Later packets report pool alone vs pool + your words (pool_gain)."]
    P, Q, C = (sum(g[x] for g in gains) for x in ("pool", "pooled", "alone"))
    lines = [f"POOL (valid words of accepted candidates so far, development only): pool alone certifies {P}/"
             f"{len(gains)} of these families; pool + your words {Q}/{len(gains)} (pool_gain {Q - P}); your words "
             f"alone {C}/{len(gains)}. Selection uses your words alone; the pool shows which words combine."]
    for g in [g for g in gains if g["pooled"] and not g["pool"] and not g["alone"]][:n]:
        others = ", ".join(f"B={o['B']} beta={o['beta']} (from {o['source'][:8]})" for o in g["others"][:3])
        lines.append((f"  newly certifiable: {g['id']} ({fams_by_id[g['id']].get('class')}): your words "
                      f"{g['yours']} + pool words {others or 'none'}")[:320])
    return lines


# ------------------------------------------------------------------- verifier
class C2Verifier(bb.BoundVerifier):
    """bound_backends.BoundVerifier with packet v2; refuses any family outside the development set."""

    def __init__(self, *args, hint=None, forbidden_ids=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.hint = list(hint or [])
        leak = set(self.by_id) & set(forbidden_ids)
        if leak:
            raise ValueError(f"validation/holdout families in the engine set: {sorted(leak)[:3]}")
        self.pool = WordPool(self.evidence.parent / "pool.json", self.by_id, forbidden_ids)
        self.family_rows = {}  # candidate hash -> {family id: row}, for GEPA's per-family evaluations

    def _admit(self, rows, digest):
        if any([self.pool.add(r, digest) for r in rows]):
            self.pool.save()

    def pool_stats(self, rows) -> tuple:
        gains = [self.pool.gain(r) for r in rows]
        return gains, {"pool_certified": sum(g["pool"] for g in gains),
                       "pooled_certified": sum(g["pooled"] for g in gains),
                       "pool_gain": sum(g["pooled"] for g in gains) - sum(g["pool"] for g in gains)}

    def evaluate(self, source: str, family_id=None, *, final=False) -> dict:
        from integrations import bound_evaluator as E

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
            res = E.evaluate(path, subset, jobs=self.jobs, cache_dir=self.cache_dir,
                             require_os_sandbox=self.require_os_sandbox)
            promising = False
            if family_id is None:
                prior, _ = self._current_best()
                promising = res["valid"] == res["families"] and (prior is None or res["combined_score"] >= prior["score"])
                if promising and digest not in self.state["screen_valid_source_hashes"]:
                    self.state["screen_valid_source_hashes"].append(digest)
            full = None
            if promising or final:
                full = E.evaluate(path, self.full, jobs=self.jobs, cache_dir=self.cache_dir,
                                  require_os_sandbox=self.require_os_sandbox)
                self.state["full_evaluations"] += 1
            # pool statistics against the pool of OTHER accepted candidates, then admission
            pool_was_empty = not self.pool.entries
            gains, pstats = self.pool_stats(res["results"])
            fpool = self.pool_stats(full["results"])[1] if full else {}
            if full:  # seed, promising and final candidates: every development family
                self._admit(full["results"], digest)
            elif family_id:  # GEPA: accepted once evaluated on the whole valset (the screen)
                seen = self.family_rows.setdefault(digest, {"rows": {}, "admitted": False})
                seen["rows"][family_id] = res["results"][0]
                if set(self.screen_ids) <= set(seen["rows"]) and not seen["admitted"]:
                    self._admit(list(seen["rows"].values()), digest)
                    seen["admitted"] = True
            fsum = ({"combined_score": full["combined_score"], "certified": full["certified"],
                     "valid": full["valid"], "families": full["families"], "max_W": full["max_W"],
                     "per_m_certified": {m: g["certified"] for m, g in full["per_m"].items()},
                     "per_m": {m: {x: g[x] for x in ("certified", "families", "pct", "boundary", "invalid",
                                                    "incomplete", "timeouts", "W", "W_complete", "G", "per_k")}
                               for m, g in full["per_m"].items()},
                     "cache_key": full["cache_key"], **fpool} if full else None)
            row = {"scope": scope, "candidate_hash": digest, "combined_score": res["combined_score"],
                   "certified": res["certified"], "valid": res["valid"], "families": res["families"],
                   "cache_hit": res["cache_hit"], "full": fsum, **pstats}
            bs, bf = self._current_best(extra=row)
            self.state["best_screen"], self.state["best_full"] = bs, bf
            if self.baseline is None and full:
                self.baseline = "seed full development: " + ", ".join(
                    f"m={m} {g['certified']}/{g['families']}" for m, g in full["per_m"].items())
            feedback = packet_v2(res, self.by_id, self._best_text(bs, bf), scope, self.baseline, self.hint,
                                 pool_lines(gains, self.by_id, empty=pool_was_empty))
            part1, part2 = bb.split_packet(feedback)
            example = E.per_example_metric(res["results"][0]) if family_id else None
            summary = {"combined_score": res["combined_score"], "certified": res["certified"], "valid": res["valid"],
                       "families": res["families"], "boundary": res["boundary"], "incomplete": res["incomplete"],
                       "timeouts": res["timeouts"], "max_W": res["max_W"], "max_W_float": float(Fr(res["max_W"])),
                       "scope": scope, "example_score": example, "candidate_hash": digest,
                       "cache_hit": res["cache_hit"], "evaluation_cache_key": res["cache_key"],
                       "feedback": feedback, "feedback_part1": part1, "feedback_part2": part2, "full": fsum,
                       **pstats}
            artifact = self.evidence / f"result-{ordinal:04d}.json"
            artifact.write_text(json.dumps({"summary": summary, "stage": res, "full": full}, default=str) + "\n")
            summary["evaluation"] = str(artifact)
            row.update(ordinal=ordinal, packet_sha256=_sha(feedback.encode()))
            self.state["evaluations"].append(row)
            return summary


# ------------------------------------------------------------------- configs
def campaign(camp=CAMP):
    camp = Path(camp)
    return _load(camp / "campaign-config.json"), _load(camp / "broker-config.json")


def frozen_paths(cc):
    """(c1 development.json, c1 frozen manifest, c2 manifest) with hash checks; never the validation/holdout."""
    man_path = ROOT / cc["frozen_manifest"]
    man = _load(man_path)
    dev = ROOT / man["development"]["path"]
    c1_man = ROOT / man["development"]["c1_manifest"]
    if _sha(dev.read_bytes()) != man["development"]["sha256"] or \
            _sha(c1_man.read_bytes()) != man["development"]["c1_manifest_sha256"]:
        raise RuntimeError("development set or campaign 1 manifest differs from the c2 manifest")
    return dev, c1_man, man_path


def forbidden_ids(cc) -> set:
    """Validation and holdout family ids (read only to assert they never reach an engine)."""
    man_path = ROOT / cc["frozen_manifest"]
    out = set()
    for name in ("validation.json", "holdout.json"):
        p = man_path.parent / name
        if p.is_file():
            out |= {f["id"] for f in _load(p)["families"]}
    return out


def pool(bc) -> int:
    """Shared contact pool: min(floor(max_usd / conservative reservation), 400)."""
    return min(int(bc["max_usd"] // bc["reservation_usd_per_request_conservative"]), 400)


def ledger_path(camp, bc, engine, seed) -> Path:
    base = Path(bc["ledger"])
    return ROOT / base.with_name(f"{base.stem}.{engine}-s{seed}{base.suffix}")


def c2_ledgers(camp, bc):
    base = ROOT / Path(bc["ledger"])
    return sorted(p for p in base.parent.glob(base.stem + ".*" + base.suffix))


def spend(camp, bc, exclude=None) -> dict:
    used = usd = 0
    for p in c2_ledgers(camp, bc):
        if exclude and p.resolve() == Path(exclude).resolve():
            continue
        attempts = _load(p).get("attempts", [])
        used += len(attempts)
        usd += sum(a.get("charged_usd") or 0.0 for a in attempts)
    return {"contacts": used, "charged_usd": usd}


def effective_iterations(cc, engine) -> int:
    """Proposals one run may make: configured iterations, capped by the run's contact sub-cap."""
    arm = cc["engines"][engine]
    return min(int(arm["iterations"]), int(arm["max_requests"]))


def engine_knobs(cc, bc, engine, seed) -> dict:
    """Every engine setting of one (arm, seed); used by the launcher and the approval hash."""
    arm = cc["engines"][engine]
    it = effective_iterations(cc, engine)
    knobs = {"engine": engine, "seed": int(seed), "iterations_configured": int(arm["iterations"]),
             "iterations_effective": it, "max_requests": int(arm["max_requests"]), "max_evals": int(arm["max_evals"]),
             "wall_seconds": int(arm["wall_seconds"]), "model": bc["model"], "max_tokens": bc["max_tokens"],
             "reasoning_effort": bc["reasoning_effort"]}
    if engine == "gepa":
        knobs["gepa"] = {"seed": int(seed), "max_candidate_proposals": it, "reflection_minibatch_size": 3,
                         "max_workers": 1, "parallel": False}
    elif engine in ("adaevolve", "evox"):
        ns = argparse.Namespace(iterations=it, model=bc["model"], broker_url="<BROKER>", max_tokens=bc["max_tokens"],
                                llm_timeout=int(bc["timeout"]) + 30, reasoning_effort=bc["reasoning_effort"],
                                engine=engine, eval_timeout=int(cc["eval_timeout"]), python=None)
        knobs["sky"] = sky_config(ns, None, seed, template_dir="<STAGED adaevolve template, sample diff removed>")
    return knobs


def sky_config(args, stage, seed, template_dir=None) -> dict:
    if template_dir is None and args.engine == "adaevolve":
        config = bb.sky_config_dict(args, stage)
    else:
        engine = args.engine
        args.engine = "evox" if engine == "evox" else "gepa"  # skip the template lookup for knob rendering
        config = bb.sky_config_dict(args, stage)
        args.engine = engine
        config["search"]["type"] = engine
        config["search"]["switch_interval"] = args.iterations + 1 if engine == "evox" else None
        config["search"]["share_llm"] = engine == "evox"
        if engine == "adaevolve":
            config["prompt"]["template_dir"] = template_dir
    config["search"]["database"]["random_seed"] = int(seed)
    return config


# ------------------------------------------------------------------- runs
def _finish(manifest, run_dir, verifier, seed_eval, best_source):
    manifest = bb._finish(manifest, run_dir, verifier, seed_eval, best_source)
    manifest["word_pool"] = dict(verifier.pool.summary(), path=str(verifier.pool.path),
                                 note="development only; pooled certificates are not a uniform program")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    return manifest


def _setup(args, engine, cc):
    dev, c1_man, _ = frozen_paths(cc)
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
    hint = (cc.get("reversal_hint") or {}).get("lines") if (cc.get("reversal_hint") or {}).get("enabled") else None
    verifier = C2Verifier(dev, run_dir, cache_dir=ROOT / cc["eval_cache"], engine=engine, provenance=provenance,
                          max_requests=args.max_evals, jobs=args.jobs, hint=hint, forbidden_ids=forbidden_ids(cc))
    (stage / "dataset.json").write_text(json.dumps({
        "train": [f["id"] for f in verifier.full if f["id"] not in set(verifier.screen_ids)],
        "screen": verifier.screen_ids}) + "\n")
    seed_eval = verifier.evaluate(seed.read_text(), final=True)
    return run_dir, stage, seed, verifier, provenance, seed_eval


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    data = json.loads(args.dataset.read_text())
    train = [{"id": f} for f in data["train"]]
    val = [{"id": f} for f in data["screen"]]
    lm = bb.BoundBrokerLM(args.broker_url, args.model, args.max_tokens, None, args.llm_timeout, args.reasoning_effort)
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
    shutil.copyfile(Path(ob.__file__), stage / "official_backends.py")
    shutil.copyfile(Path(lb.__file__), stage / "lift_backends.py")
    shutil.copyfile(Path(bb.__file__), stage / "bound_backends.py")
    shutil.copyfile(Path(__file__), stage / "bound_c2_worker.py")
    server, verifier_url = verifier.serve()
    env = ob._worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "bound_c2_worker.py"), "_gepa_worker",
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
    return _finish(manifest, run_dir, verifier, seed_eval, trusted_best.read_text())


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
    return _finish(manifest, run_dir, verifier, seed_eval, best_source)


def run(args) -> dict:
    cc, _ = campaign(args.campaign_dir)
    return _sequential(args, cc) if args.engine == "sequential" else _launch(args, cc)


# ------------------------------------------------------------------- first prompts
def first_prompt_file(camp, engine, seed) -> Path:
    return Path(camp) / f"first-prompt-{engine}-s{seed}.sha256"


def _read_hash(path):
    return Path(path).read_text().split()[0] if Path(path).is_file() else None


def captured_first(capture_dir, engine):
    """(path, messages) of the arm's first proposer request in a mock capture."""
    role = {"gepa": "gepa_reflection", "sequential": "sequential_refinement"}.get(engine)
    for path in sorted(Path(capture_dir).glob("request-*.json")):
        item = _load(path)
        if (item["role"] == role) if role else bb.is_solution_request(item["body"].get("messages")):
            return path, item["body"]
    raise FileNotFoundError(f"no captured first {engine} proposer request in {capture_dir}")


def write_first_prompt(capture_dir, engine, seed, camp=CAMP) -> str:
    path, body = captured_first(capture_dir, engine)
    messages = body["messages"]
    digest = lb.messages_sha256(messages)
    target = first_prompt_file(camp, engine, seed)
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
    from integrations.bound_evaluator import CONTRACT, VERSION, evaluator_hash
    from integrations.research_budget import _dry_run_payload

    camp = Path(camp)
    cc, bc = campaign(camp)
    dev, c1_man, man_path = frozen_paths(cc)
    man = _load(man_path)
    knobs, prompts = {}, {}
    for engine in ARMS:
        for seed in cc["seeds"]:
            knobs[f"{engine}/s{seed}"] = engine_knobs(cc, bc, engine, seed)
            prompts[f"{engine}/s{seed}"] = _read_hash(first_prompt_file(camp, engine, seed))
    code = {n: _sha(Path(f).read_bytes()) for n, f in (("bound_c2", __file__), ("bound_backends", bb.__file__),
                                                        ("lift_backends", lb.__file__),
                                                        ("official_backends", ob.__file__))}
    for n in ("research_budget", "bound_c2_finalize", "program_sandbox"):
        code[n] = _sha((ROOT / "integrations" / f"{n}.py").read_bytes())
    return {"campaign_config": cc, "broker_config": bc, "pool": pool(bc), "engine_knobs": knobs,
            "first_prompts": prompts,
            "upstream_endpoint": bc["upstream_url"].rstrip("/") + "/chat/completions",
            "dry_run_payload": _dry_run_payload(bc),
            "prompts": {"system": SYSTEM, "objective": OBJECTIVE, "mechanism": bb.MECHANISM,
                        "reversal_hint": cc.get("reversal_hint")},
            "word_pool": {"scope": "development only", "admission": "seed, promising and final candidates "
                          "(full development rows); GEPA candidates once evaluated on every screen family",
                          "pruning": "Pareto on (B, beta)", "pool_gain": "pooled certified minus pool-alone "
                          "certified over the evaluated families", "selection": "standalone only"},
            "packet_format": {"marker": PACKET_MARK, "max_chars": PACKET_MAX, "artifact_max": bb.ARTIFACT_MAX,
                              "scope": "development only", "failing_families": 3,
                              "reversal_orbit_lines": ["order class", "binding at gap-LP optimum",
                                                       "best single word crossing profile"]},
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
                "--iterations", str(min(effective_iterations(cc, args.engine), b["contacts"])),
                "--max-evals", str(arm["max_evals"]), "--wall-seconds", str(arm["wall_seconds"]),
                "--llm-timeout", str(int(bc["timeout"]) + 30), "--eval-timeout", str(cc["eval_timeout"]),
                "--python", str(ROOT / cc["python"]), "--ledger", str(b["ledger"])]
        expected = _read_hash(first_prompt_file(camp, args.engine, args.seed))
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
    fp.add_argument("--write", action="store_true", help="write first-prompt-<engine>-s<seed>.{md,sha256}")
    for name in ("approval-hash", "check-approval", "campaign-spend", "live"):
        a = sub.add_parser(name)
        a.add_argument("--campaign-dir", type=Path, default=CAMP)
        if name == "approval-hash":
            a.add_argument("--write-material", type=Path)
        if name == "live":
            a.add_argument("--engine", required=True, choices=ARMS)
            a.add_argument("--seed", required=True, type=int)
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
    if args.action == "first-prompt":
        if args.write:
            print(write_first_prompt(args.capture_dir, args.engine, args.seed))
        else:
            print(lb.messages_sha256(captured_first(args.capture_dir, args.engine)[1]["messages"]))
        return
    if args.action == "_gepa_worker":
        return _gepa_worker(args)
    result = run(args) if args.action == "run" else _live(args)
    keep = ("engine", "seed", "status", "research_status", "run_dir", "seed_full", "verified_best_full")
    print(json.dumps({k: result.get(k) for k in keep}, default=str))


if __name__ == "__main__":
    main()
