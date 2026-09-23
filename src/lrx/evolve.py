"""Campaign runner with pluggable search engines.

Engines (all share proposer, evaluator, budgets and logging):
  best_of_n   independent proposals from the seeds (no accumulated feedback)
  sequential  hill climbing: always refine the current best
  gepa        GEPA-style: Pareto front over per-graph scores, P x N reflective
              mutations (gepa_n children per parent), merge of two front
              members only after a new best is found (at most max_merges)
  adaevolve   AdaEvolve-style: islands, decayed UCB island selection with
              rewards normalised by the global best, per-island exploration
              intensity I = I_min + (I_max - I_min) / (1 + sqrt(G)),
              migration, meta-guidance on global stagnation
  evox        EvoX-style: the search strategy (a validated JSON policy, never
              code) is scored per window of proposals and replaced by the
              reflector when a window brings no improvement

Options for every engine: `async` keeps `batch` proposals in flight and plans
each new request from the current archive; `history` and `inspirations` put
recent attempts and other archive members into prompts; `focus` points each
request at the graph where its parent lags most; `tactics` turns reflection
into structured tactics whose outcomes are tracked and fed back.

These are compact re-implementations of the published ideas, not the official
GEPA/SkyDiscover/EvoX packages. Held-out graphs are evaluated only at the end
and never shown to a proposer.
"""

import concurrent.futures as cf
import hashlib
import json
import math
import multiprocessing
import os
import random
import subprocess
import time
from pathlib import Path

from . import evaluator, prompt
from .candidates import Candidate, CandidateError, canonical_json
from .feedback import compress
from .llm import BudgetExhausted

ENGINES = ("best_of_n", "sequential", "gepa", "adaevolve", "evox")
DEFAULTS = {
    "engine": "adaevolve",
    "kinds": ["rules"],
    "seeds": [],
    "split": "train",
    "max_proposals": 40,
    "batch": 4,
    "seed": 0,
    "eval_workers": 4,
    "max_wall_seconds": 3600,
    "islands": 3,
    "island_size": 6,
    "migration_every": 12,
    "stagnation": 12,
    "ucb_c": math.sqrt(2),
    "ucb_decay": 0.9,
    # GEPA: probability of using a merge opportunity (one opens after each new best)
    "merge_prob": 1.0,
    "max_merges": 5,
    "gepa_n": 1,
    "final_heldout_top": 3,
    "insights_file": None,
    "provider": {"type": "offline"},
    "reflector": None,
    "refine_mode": "exploit",
    "explore_max": 0.7,
    "feedback_words": False,
    "feedback_potential": True,
    "async": False,
    "history": 0,
    "inspirations": 0,
    "focus": False,
    "tactics": False,
    "tactic_trials": 3,
    "window": 4,
    "strategy": None,
    "select": "score",
}
REFINE_MODES = ("exploit", "edit")
SELECTS = ("score", "failures")
INT_LIMITS = {
    "gepa_n": (1, 8),
    "max_merges": (0, 100),
    "history": (0, 12),
    "inspirations": (0, 4),
    "tactic_trials": (1, 20),
    "window": (1, 100),
}
G_DECAY = 0.9
MAX_TACTICS = 4
EVOX_START = {
    "parent": "best",
    "modes": {"exploit": 1.0},
    "inspirations": 0,
    "inspiration_pool": "top",
    "history": 4,
    "focus": False,
    "tactic": None,
}
PARENT_RULES = ("best", "front", "top3", "random")
STRATEGY_MODES = ("exploit", "explore", "edit", "merge")


def validate_strategy(obj):
    """Return (strategy, None) or (None, reason). A strategy is data only."""
    if not isinstance(obj, dict):
        return None, "strategy must be a JSON object"
    unknown = set(obj) - set(EVOX_START) - {"name", "rationale"}
    if unknown:
        return None, f"unknown strategy keys {sorted(unknown)}"
    s = dict(EVOX_START, **{k: v for k, v in obj.items() if k in EVOX_START})
    if s["parent"] not in PARENT_RULES:
        return None, f"parent must be one of {list(PARENT_RULES)}"
    modes = s["modes"]
    if not isinstance(modes, dict) or not modes or set(modes) - set(STRATEGY_MODES):
        return None, f"modes must map a subset of {list(STRATEGY_MODES)} to weights"
    if (
        any(type(w) not in (int, float) or w < 0 for w in modes.values())
        or sum(modes.values()) <= 0
    ):
        return None, "mode weights must be non-negative numbers with a positive sum"
    for key, hi in (("inspirations", 3), ("history", 8)):
        if type(s[key]) is not int or not 0 <= s[key] <= hi:
            return None, f"{key} must be an integer 0..{hi}"
    if s["inspiration_pool"] not in ("top", "random"):
        return None, "inspiration_pool must be top or random"
    if type(s["focus"]) is not bool:
        return None, "focus must be true or false"
    if s["tactic"] is not None and (
        not isinstance(s["tactic"], str) or len(s["tactic"]) > 800
    ):
        return None, "tactic must be null or a string of at most 800 characters"
    s["modes"] = {k: float(v) for k, v in modes.items()}
    return s, None


def parse_tactics(text):
    """JSON tactics from reflector text: [{idea, how, target, cautions}]."""
    data = None
    if "```json" not in text and "[" in text:
        try:
            data, _ = json.JSONDecoder().raw_decode(text[text.index("[") :])
        except json.JSONDecodeError:
            data = None
    if data is None:
        try:
            data = prompt.extract_candidate(text)
        except ValueError:
            return []
    if isinstance(data, dict):
        data = data.get("tactics", [data])
    if not isinstance(data, list):
        return []
    out = []
    for item in data[:MAX_TACTICS]:
        if isinstance(item, dict) and str(item.get("idea", "")).strip():
            out.append(
                {
                    k: str(item[k])[:500]
                    for k in ("idea", "how", "target", "cautions")
                    if item.get(k)
                }
            )
    return out


def _eval_job(args):
    spec, split = args
    return evaluator.evaluate(spec, split=split)


def _git_commit():
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=evaluator.ROOT_DIR,
                timeout=5,
            ).stdout.strip()
            or None
        )
    except (OSError, subprocess.SubprocessError):
        return None


class Campaign:
    def __init__(self, cfg, run_dir, proposer):
        unknown = set(cfg) - set(DEFAULTS) - {"name", "description"}
        if unknown:
            raise ValueError(f"unknown campaign keys {sorted(unknown)}")
        self.cfg = dict(DEFAULTS, **cfg)
        if self.cfg["engine"] not in ENGINES:
            raise ValueError(f"engine must be one of {ENGINES}")
        if self.cfg["refine_mode"] not in REFINE_MODES:
            raise ValueError(f"refine_mode must be one of {REFINE_MODES}")
        if self.cfg["select"] not in SELECTS:
            raise ValueError(f"select must be one of {SELECTS}")
        for key in ("explore_max", "merge_prob", "ucb_decay"):
            if not 0.0 <= self.cfg[key] <= 1.0:
                raise ValueError(f"{key} must be in [0, 1]")
        for key, (lo, hi) in INT_LIMITS.items():
            value = self.cfg[key]
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError(f"{key} must be an integer {lo}..{hi}")
        self.strategy = None
        if self.cfg["engine"] == "evox":
            self.strategy, err = validate_strategy(self.cfg["strategy"] or EVOX_START)
            if err:
                raise ValueError(f"strategy: {err}")
        self.run_dir = Path(run_dir)
        if self.run_dir.exists():
            raise FileExistsError(f"run directory exists: {self.run_dir}")
        self.run_dir.mkdir(parents=True)
        self.proposer = proposer
        self.rng = random.Random(self.cfg["seed"])
        self.records = []
        self.by_hash = {}
        self.insights = []
        self.proposals = 0
        self.completed = 0
        self.inflight = []
        self.stop_reason = None
        self.best_id = None
        self.since_improvement = 0
        self.batches = 0
        self.started = time.time()
        self.islands = [
            {"members": [], "G": 0.0, "visits": 0.0, "reward": 0.0, "planned": 0}
            for _ in range(max(1, self.cfg["islands"]))
        ]
        self.tactics = []
        self.tactic_turn = 0
        self.need_tactics = False
        self.merge_credit = False
        self.merges = 0
        self.strategy_history = []
        self.window_start = None
        self.window_count = 0
        self.reflection = None
        self.reflect_pool = None
        self._events = open(self.run_dir / "events.jsonl", "x")
        self._tsv = open(self.run_dir / "results.tsv", "x")
        self._tsv.write(
            "iteration\tid\thash\tkind\tmode\tisland\tparent\tscore"
            "\tfeasible\tstatus\tcost_usd\tname\n"
        )
        (self.run_dir / "config.json").write_text(json.dumps(self.cfg, indent=2) + "\n")
        base_insights = self.cfg.get("insights_file")
        if base_insights and Path(base_insights).exists():
            self.insights.append(Path(base_insights).read_text()[:4000])

    # ------------------------------------------------------------------ utils
    def store_prompt(self, messages):
        """Save the (large, repeated) system prompt once; return trace fields."""
        if not messages:
            return {}
        fields = {}
        rest = []
        for msg in messages:
            if msg["role"] == "system":
                sha = hashlib.sha256(msg["content"].encode()).hexdigest()[:16]
                path = self.run_dir / "prompts" / f"system-{sha}.txt"
                if not path.exists():
                    path.parent.mkdir(exist_ok=True)
                    path.write_text(msg["content"])
                fields["prompt_system_sha"] = sha
            else:
                rest.append(msg)
        fields["prompt_messages"] = rest
        return fields

    def store_eval(self, result):
        """Full evaluator result, one file per candidate hash."""
        key = result.get("candidate_hash")
        if not key or "duplicate_of" in result:
            return
        path = self.run_dir / "evals" / f"{key}.json"
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps(result, default=str))

    def log(self, event, **data):
        data = dict(event=event, t=round(time.time() - self.started, 2), **data)
        self._events.write(json.dumps(data, sort_keys=True, default=str) + "\n")
        self._events.flush()

    def record(self, rec, status):
        self._tsv.write(
            "\t".join(
                str(x)
                for x in [
                    self.proposals,
                    rec["id"],
                    rec.get("hash"),
                    rec.get("kind"),
                    rec.get("mode"),
                    rec.get("island"),
                    ",".join(map(str, rec.get("parents", []))),
                    rec.get("score"),
                    rec.get("feasible"),
                    status,
                    rec.get("cost_usd", 0),
                    (rec.get("spec") or {}).get("name", ""),
                ]
            )
            + "\n"
        )
        self._tsv.flush()

    def best(self):
        return self.records[self.best_id] if self.best_id is not None else None

    @staticmethod
    def failures(rec):
        return sum(
            g.get("failures") or 0
            for g in rec["eval"].get("graphs", [])
            if g.get("feedback")
        )

    def rank(self, rec):
        """Selection key, higher is better. With select "failures", candidates
        that pass sanity come first, then fewer failures on feedback graphs,
        then score. The evaluator's score itself is never changed."""
        if self.cfg["select"] == "score":
            return (rec["score"],)
        return (not rec["eval"].get("stopped"), -self.failures(rec), rec["score"])

    def sel_instances(self, rec):
        """Per-graph values used for the Pareto front and focus."""
        if self.cfg["select"] == "score":
            return rec["instances"]
        return {
            g["graph"]: -(g.get("failures") or 0)
            for g in rec["eval"].get("graphs", [])
            if g.get("feedback")
        }

    def ranked(self, pool):
        return sorted(pool, key=self.rank, reverse=True)

    def archive(self):
        """Distinct, valid, fully evaluated candidates; if there are none (all
        stopped at sanity, usual for potentials), the sanity-stopped ones."""
        distinct = [
            r for r in self.records if r["valid"] and "duplicate_of" not in r["eval"]
        ]
        return [r for r in distinct if not r["eval"].get("stopped")] or distinct

    # ------------------------------------------------------------- evaluation
    def evaluate_specs(self, specs, pool):
        """Evaluate specs (deduplicated by candidate hash). Returns results list."""
        results = [None] * len(specs)
        jobs = {}
        for i, spec in enumerate(specs):
            if spec is None:
                continue
            try:
                cand = Candidate(spec)
            except CandidateError as exc:
                results[i] = {
                    "valid": False,
                    "error": str(exc),
                    "score": -1e6,
                    "feasible": False,
                    "instances": {},
                    "graphs": [],
                }
                continue
            if cand.kind not in self.cfg["kinds"]:
                results[i] = {
                    "valid": False,
                    "score": -1e6,
                    "feasible": False,
                    "error": f"kind {cand.kind} not allowed in this campaign",
                    "instances": {},
                    "graphs": [],
                }
                continue
            if cand.hash in self.by_hash:
                results[i] = dict(
                    self.records[self.by_hash[cand.hash]]["eval"],
                    duplicate_of=self.by_hash[cand.hash],
                )
                continue
            jobs[i] = pool.submit(_eval_job, (spec, self.cfg["split"]))
        for i, fut in jobs.items():
            results[i] = fut.result()
        return results

    def feedback_spec(self, spec):
        kind = (spec or {}).get("kind")
        if kind == "potential":
            return spec if self.cfg["feedback_potential"] else None
        return spec if self.cfg["feedback_words"] else None

    def add(self, spec, result, mode, parents, island, extra):
        rec = {
            "id": len(self.records),
            "hash": result.get("candidate_hash"),
            "kind": result.get("kind"),
            "spec": spec,
            "mode": mode,
            "parents": parents,
            "island": island,
            "score": result.get("score"),
            "feasible": result.get("feasible"),
            "instances": result.get("instances", {}),
            "valid": result.get("valid", False),
            "eval": result,
            "feedback": compress(result, spec=self.feedback_spec(spec)),
            **extra,
        }
        self.records.append(rec)
        self.store_eval(result)
        duplicate = "duplicate_of" in result
        if rec["valid"] and not duplicate and rec["hash"]:
            self.by_hash[rec["hash"]] = rec["id"]
        improved = False
        if rec["valid"] and not duplicate:
            best = self.best()
            if best is None or self.rank(rec) > self.rank(best):
                self.best_id = rec["id"]
                improved = True
        status = (
            "invalid"
            if not rec["valid"]
            else "duplicate"
            if duplicate
            else "keep"
            if improved
            else "discard"
        )
        self.log(
            "candidate",
            **{k: v for k, v in rec.items() if k != "eval"},
            graphs=[
                {
                    k: g.get(k)
                    for k in (
                        "graph",
                        "score",
                        "failures",
                        "incomplete",
                        "value_max",
                        "excess_T",
                        "gap_mean",
                    )
                }
                for g in result.get("graphs", [])
            ],
            status=status,
            seconds=result.get("seconds"),
        )
        rec["status"] = status
        self.record(rec, status)
        return rec, improved

    # --------------------------------------------------------------- planning
    def plan(self, k=None):
        """Return k proposal requests: dicts(mode, parents(list of ids), island).

        Requests already in flight count as pending, so an asynchronous run
        plans one request at a time against the same constraints as a batch."""
        k = self.cfg["batch"] if k is None else k
        if not any(r["mode"] == "seed" and r["valid"] for r in self.records):
            raise RuntimeError("no valid seed candidates")
        opts = self.strategy if self.cfg["engine"] == "evox" else self.cfg
        out = []
        for _ in range(k):
            pending = self.inflight + out
            req = self.plan_one(pending)
            if opts["focus"] and req["mode"] != "merge":
                taken = {
                    (p.get("focus") or {}).get("graph")
                    for p in pending
                    if p["parents"] == req["parents"]
                }
                focus = self.focus_for(req["parents"][0], taken)
                if focus:
                    req["focus"] = focus
            self.assign_tactic(req)
            out.append(req)
        return out

    def plan_one(self, pending):
        engine = self.cfg["engine"]
        refine = self.cfg["refine_mode"]
        if engine == "best_of_n":
            seeds = [
                r["id"] for r in self.records if r["mode"] == "seed" and r["valid"]
            ]
            return {"mode": "explore", "parents": [self.rng.choice(seeds)], "island": 0}
        if engine == "sequential":
            return {"mode": refine, "parents": [self.best_id], "island": 0}
        if engine == "gepa":
            return self.plan_gepa(pending)
        if engine == "evox":
            return self.plan_evox()
        return self.plan_adaevolve(pending)

    def merge_request(self, front):
        """Merge the best front member with the one that beats it most often."""
        a = self.best_id if self.best_id in front else max(front, key=front.get)
        inst_a = self.sel_instances(self.records[a])
        others = [i for i in sorted(front) if i != a]

        def wins_over_a(i):
            inst = self.sel_instances(self.records[i])
            return sum(inst.get(g, -1e9) > s for g, s in inst_a.items())

        b = max(others, key=lambda i: (wins_over_a(i), front[i]))
        self.merges += 1
        return {"mode": "merge", "parents": [a, b], "island": 0}

    def plan_gepa(self, pending):
        front = self.pareto_front()
        if (
            self.merge_credit
            and len(front) > 1
            and self.merges < self.cfg["max_merges"]
            and self.rng.random() < self.cfg["merge_prob"]
        ):
            self.merge_credit = False
            return self.merge_request(front)
        load = {}
        for p in pending:
            if p["mode"] != "merge":
                load[p["parents"][0]] = load.get(p["parents"][0], 0) + 1
        ids = sorted(front)
        room = [i for i in ids if load.get(i, 0) < self.cfg["gepa_n"]] or ids
        # P x N: fill an open parent's N children before sampling another parent.
        started = [i for i in room if load.get(i, 0) > 0]
        if started:
            parent = started[0]
        else:
            parent = self.rng.choices(room, weights=[front[i] for i in room])[0]
        return {"mode": self.cfg["refine_mode"], "parents": [parent], "island": 0}

    def plan_evox(self):
        s = self.strategy
        modes = sorted(s["modes"])
        mode = self.rng.choices(modes, weights=[s["modes"][m] for m in modes])[0]
        if mode == "edit" and "rules" not in self.cfg["kinds"]:
            mode = "exploit"
        if mode == "merge":
            front = self.pareto_front()
            if len(front) > 1:
                return self.merge_request(front)
            mode = "exploit"
        pool = self.ranked(self.archive())
        rule = s["parent"]
        if rule == "front":
            front = self.pareto_front()
            ids = sorted(front)
            parent = self.rng.choices(ids, weights=[front[i] for i in ids])[0]
        elif rule == "top3" and pool:
            parent = self.rng.choice(pool[:3])["id"]
        elif rule == "random" and pool:
            parent = self.rng.choice(pool)["id"]
        else:
            parent = self.best_id
        return {"mode": mode, "parents": [parent], "island": 0}

    def plan_adaevolve(self, pending):
        island = self.select_island(pending)
        state = self.islands[island]
        members = sorted(state["members"], key=lambda i: -self.records[i]["score"])
        cap = self.cfg["explore_max"]
        low = min(0.1, cap)
        explore_p = low + (cap - low) / (1.0 + math.sqrt(state["G"] + 1e-12))
        if self.rng.random() < explore_p:
            parent = self.rng.choice(members)
            mode = "explore"
        else:
            parent = members[0]
            mode = self.cfg["refine_mode"]
        state["planned"] += 1
        return {
            "mode": mode,
            "parents": [parent],
            "island": island,
            "explore_p": round(explore_p, 3),
        }

    def focus_for(self, parent, taken):
        """Graph where the parent lags the archive most (then its worst graph)."""
        inst = self.sel_instances(self.records[parent])
        if not inst:
            return None
        pool = [self.sel_instances(r) for r in self.archive()] or [inst]
        best = {g: max(p.get(g, -1e9) for p in pool) for g in inst}
        ranked = sorted(inst, key=lambda g: (inst[g] - best[g], inst[g], g))
        free = [g for g in ranked if g not in taken] or ranked
        g = free[0]
        if self.cfg["select"] == "failures":
            return {"graph": g, "parent_failures": -inst[g], "archive_fewest": -best[g]}
        return {"graph": g, "parent_score": inst[g], "archive_best": best[g]}

    def pareto_front(self):
        """GEPA front: candidates best (ties allowed) on >= 1 instance -> weight."""
        pool = self.archive()
        if not pool:
            return {self.best_id: 1}
        values = {r["id"]: self.sel_instances(r) for r in pool}
        instances = sorted({k for v in values.values() for k in v})
        wins = {}
        for inst in instances:
            top = max(v.get(inst, -1e9) for v in values.values())
            for rid, v in values.items():
                if v.get(inst, -1e9) == top:
                    wins[rid] = wins.get(rid, 0) + 1
        # Drop members dominated on every instance by another front member.
        front = dict(wins)
        for a in list(front):
            for b in list(front):
                if a != b and b in front and a in front:
                    ra, rb = values[a], values[b]
                    if all(
                        rb.get(i, -1e9) >= ra.get(i, -1e9) for i in instances
                    ) and any(rb.get(i, -1e9) > ra.get(i, -1e9) for i in instances):
                        del front[a]
                        break
        return front or {self.best_id: 1}

    def select_island(self, pending=()):
        """UCB over decayed island rewards; in-flight requests count as pulls."""
        inflight = {}
        for p in pending:
            inflight[p["island"]] = inflight.get(p["island"], 0) + 1
        pulls = [s["visits"] + inflight.get(i, 0) for i, s in enumerate(self.islands)]
        total = sum(pulls) + 1
        best, best_val = 0, -1e18
        for i, s in enumerate(self.islands):
            if not s["members"]:
                continue
            if s["planned"] == 0:
                return i
            mean = s["reward"] / s["visits"] if s["visits"] > 0 else 0.0
            value = mean + self.cfg["ucb_c"] * math.sqrt(
                math.log(total) / max(pulls[i], 1e-9)
            )
            if value > best_val:
                best, best_val = i, value
        return best

    def update_island(self, island, rec):
        state = self.islands[island]
        members = state["members"]
        before = max((self.records[i]["score"] for i in members), default=None)
        delta, reward = 0.0, 0.0
        if rec["valid"] and "duplicate_of" not in rec["eval"]:
            if before is not None and rec["score"] > before:
                delta = (rec["score"] - before) / (abs(before) + 1.0)
                best = self.best()
                reward = (rec["score"] - before) / (abs(best["score"]) + 1.0)
            members.append(rec["id"])
            members.sort(key=lambda i: -self.records[i]["score"])
            del members[self.cfg["island_size"] :]
        state["G"] = G_DECAY * state["G"] + (1 - G_DECAY) * delta * delta
        gamma = self.cfg["ucb_decay"]
        state["reward"] = gamma * state["reward"] + min(1.0, reward)
        state["visits"] = gamma * state["visits"] + 1.0

    def migrate(self):
        n = len(self.islands)
        if n < 2:
            return
        bests = [s["members"][0] for s in self.islands if s["members"]]
        for i, s in enumerate(self.islands):
            incoming = bests[(i - 1) % len(bests)]
            if incoming not in s["members"]:
                s["members"].append(incoming)
                s["members"].sort(key=lambda j: -self.records[j]["score"])
                del s["members"][self.cfg["island_size"] :]
        self.log("migration", islands=[s["members"][:3] for s in self.islands])

    # ---------------------------------------------------------------- context
    def recent_attempts(self, n):
        """Meta-Harness-style raw history: the last n proposals, newest first."""
        out = []
        for rec in reversed(self.records):
            if len(out) >= n:
                break
            if rec["mode"] == "seed":
                continue
            parent = self.records[rec["parents"][0]] if rec["parents"] else None
            item = {
                "id": rec["id"],
                "mode": rec["mode"],
                "parents": rec["parents"],
                "status": rec.get("status"),
                "score": rec["score"] if rec["valid"] else None,
                "parent_score": parent["score"] if parent else None,
            }
            if self.cfg["select"] == "failures" and rec["valid"]:
                item["failures"] = self.failures(rec)
                item["parent_failures"] = self.failures(parent) if parent else None
            notes = (rec.get("spec") or {}).get("notes")
            if notes:
                item["notes"] = str(notes)[:300]
            err = rec.get("proposer_error") or (
                None if rec["valid"] else rec["eval"].get("error")
            )
            if err:
                item["error"] = str(err)[:300]
            problems = [
                {k: g[k] for k in ("graph", "score", "failures", "excess_T") if k in g}
                for g in (rec.get("feedback") or {}).get("graphs", [])
                if g.get("failures") or (g.get("excess_T") or 0) > 0
            ]
            if problems:
                item["problem_graphs"] = problems[:4]
            for key in ("tactic", "focus"):
                if rec.get(key) is not None:
                    item[key] = rec[key]
            out.append(item)
        return out

    def inspirations_for(self, req, k, pool_kind):
        exclude = set(req["parents"])
        seen = {self.records[i]["hash"] for i in exclude}
        cands = []
        for r in self.ranked(self.archive()):
            if r["id"] not in exclude and r["hash"] not in seen:
                seen.add(r["hash"])
                cands.append(r)
        if pool_kind == "random":
            picks = self.rng.sample(cands, min(k, len(cands)))
        else:
            picks = cands[:k]
        return [
            {
                "id": r["id"],
                "score": r["score"],
                "graph_scores": r["instances"],
                "spec": {k: v for k, v in r["spec"].items() if k != "notes"},
            }
            for r in picks
        ]

    def context(self, req):
        evox = self.cfg["engine"] == "evox"
        opts = self.strategy if evox else self.cfg
        ctx = {}
        if opts["history"]:
            ctx["history"] = self.recent_attempts(opts["history"])
        if opts["inspirations"]:
            if evox:
                pool_kind = opts["inspiration_pool"]
            else:
                pool_kind = "random" if req["mode"] == "explore" else "top"
            ctx["inspirations"] = self.inspirations_for(
                req, opts["inspirations"], pool_kind
            )
        if req.get("focus"):
            ctx["focus"] = req["focus"]
        if req.get("tactic") is not None:
            t = self.tactics[req["tactic"]]
            ctx["tactic"] = {
                k: t[k] for k in ("idea", "how", "target", "cautions") if k in t
            }
        elif evox and self.strategy.get("tactic"):
            ctx["tactic"] = {"idea": self.strategy["tactic"]}
        return {k: v for k, v in ctx.items() if v}

    # ---------------------------------------------------------------- tactics
    def active_tactic(self, promote=True):
        for t in self.tactics:
            if t["status"] == "active":
                return t
        if promote:
            for t in self.tactics:
                if t["status"] == "queued":
                    t["status"] = "active"
                    return t
        return None

    def tactic_budget(self, t):
        return self.cfg["tactic_trials"] * (1 + t["wins"])

    def assign_tactic(self, req):
        """Every other request carries the active tactic while it has trials left."""
        if not self.cfg["tactics"] or self.cfg["engine"] == "evox":
            return
        self.tactic_turn += 1
        if self.tactic_turn % 2:
            return
        t = self.active_tactic()
        if t is None or t["trials"] >= self.tactic_budget(t):
            return
        t["trials"] += 1
        t["outstanding"] += 1
        req["tactic"] = t["id"]

    def tactic_outcome(self, req, rec, improved):
        if req.get("tactic") is None:
            return
        t = self.tactics[req["tactic"]]
        t["outstanding"] -= 1
        t["wins"] += int(improved)
        parent = self.records[rec["parents"][0]] if rec["parents"] else None
        change = (
            round(rec["score"] - parent["score"], 4)
            if rec["valid"] and parent
            else rec.get("status")
        )
        t["outcomes"].append(change)
        if (
            t["status"] == "active"
            and t["trials"] >= self.tactic_budget(t)
            and t["outstanding"] == 0
        ):
            t["status"] = "retired"
            self.log("tactic_retired", tactic=t)
            if self.active_tactic() is None:
                self.need_tactics = True

    # ------------------------------------------------------------- reflection
    def reflection_summary(self, task):
        top = self.ranked(self.archive())[:2]
        summary = {
            "task": task,
            "proposals": self.proposals,
            "remaining_proposals": self.cfg["max_proposals"] - self.proposals,
            "best": [{"spec": r["spec"], "feedback": r["feedback"]} for r in top],
            "recent_attempts": self.recent_attempts(8),
            "current_insights": self.insights[-3:],
        }
        if task == "tactics":
            summary["past_tactics"] = [
                {
                    k: t.get(k)
                    for k in ("idea", "how", "status", "trials", "wins", "outcomes")
                }
                for t in self.tactics[-8:]
            ]
        if task == "strategy":
            summary["best"] = summary["best"][:1]
            summary["current_strategy"] = self.strategy
            summary["strategy_history"] = self.strategy_history[-8:]
            summary["population"] = self.population()
        return summary

    def population(self):
        pool = sorted(self.archive(), key=lambda r: -r["score"])
        modes = {}
        for rec in self.records:
            if rec["mode"] == "seed":
                continue
            m = modes.setdefault(rec["mode"], {"n": 0, "keep": 0, "invalid": 0})
            m["n"] += 1
            m["keep"] += rec.get("status") == "keep"
            m["invalid"] += not rec["valid"]
        return {
            "archive": len(pool),
            "best_score": pool[0]["score"] if pool else None,
            "median_score": pool[len(pool) // 2]["score"] if pool else None,
            "front_size": len(self.pareto_front()),
            "modes": modes,
        }

    def start_reflection(self, task):
        if self.reflection is not None:
            return
        summary = self.reflection_summary(task)
        fut = self.reflect_pool.submit(
            self.proposer.reflect, summary, seed=self.proposals, task=task
        )
        self.reflection = (task, fut)
        if not self.cfg["async"]:
            self.poll_reflection(wait=True)

    def poll_reflection(self, wait=False):
        if self.reflection is None:
            return
        task, fut = self.reflection
        if not wait and not fut.done():
            return
        try:
            out = fut.result()
        except Exception as exc:  # a failed reflection never stops a run
            out = {"text": None, "error": f"{type(exc).__name__}: {exc}"}
        self.reflection = None
        self.apply_reflection(task, out)

    def apply_reflection(self, task, out):
        text = out.get("text")
        info = {}
        if text and task == "tactics":
            new = parse_tactics(text)
            if new:
                for t in self.tactics:
                    if t["status"] in ("queued", "active"):
                        t["status"] = "replaced"
                for fields in new:
                    self.tactics.append(
                        dict(
                            fields,
                            id=len(self.tactics),
                            status="queued",
                            trials=0,
                            wins=0,
                            outstanding=0,
                            outcomes=[],
                            created_at=self.proposals,
                        )
                    )
                info["tactics"] = new
            else:
                info["parse_error"] = "no JSON tactics; text kept as an insight"
                self.insights = (self.insights + [text[:1500]])[-3:]
        elif text and task == "strategy":
            try:
                strategy, err = validate_strategy(prompt.extract_candidate(text))
            except ValueError as exc:
                strategy, err = None, str(exc)
            if strategy:
                self.strategy = strategy
                info["strategy"] = strategy
            else:
                info["strategy_error"] = err
        elif text:
            self.insights = (self.insights + [text])[-3:]
        self.log(
            "reflection",
            task=task,
            proposals=self.proposals,
            text=text,
            error=out.get("error"),
            cost_usd=out.get("cost_usd"),
            tokens_in=out.get("tokens_in"),
            tokens_out=out.get("tokens_out"),
            llm_seconds=out.get("seconds"),
            **info,
            **self.store_prompt(out.get("messages")),
        )

    def evox_window(self, count):
        """Score the strategy per window: J = delta / (|start| + 1) / sqrt(W)."""
        best = self.best()["score"]
        if self.window_start is None:
            self.window_start = best
        self.window_count += count
        if self.window_count < self.cfg["window"]:
            return
        start, width = self.window_start, self.window_count
        delta = best - start
        entry = {
            "strategy": self.strategy,
            "start": start,
            "end": best,
            "delta": round(delta, 4),
            "J": round(delta / (abs(start) + 1.0) / math.sqrt(width), 6),
            "proposals": self.proposals,
        }
        self.strategy_history.append(entry)
        self.log("strategy_window", **entry)
        self.window_start, self.window_count = best, 0
        if delta <= 0 and self.proposals < self.cfg["max_proposals"]:
            self.start_reflection("strategy")

    # ------------------------------------------------------------------- run
    def can_submit(self):
        if self.stop_reason is not None:
            return False
        if self.proposals >= self.cfg["max_proposals"]:
            self.stop_reason = "max_proposals"
        elif time.time() - self.started > self.cfg["max_wall_seconds"]:
            self.stop_reason = "max_wall_seconds"
        return self.stop_reason is None

    def submit(self, req, threads):
        self.proposals += 1
        req["proposal"] = self.proposals
        self.inflight.append(req)
        parents = [
            (self.records[i]["spec"], self.records[i]["feedback"])
            for i in req["parents"]
        ]
        ctx = self.context(req)
        req["context"] = sorted(ctx)
        # Older proposers take no context argument; pass it only when used.
        kwargs = {"context": ctx} if ctx else {}
        return threads.submit(
            self.proposer.propose,
            req["mode"],
            parents,
            self.cfg["kinds"],
            "\n".join(self.insights) or None,
            self.cfg["seed"] * 100_000 + self.proposals,
            **kwargs,
        )

    @staticmethod
    def collect(fut):
        try:
            return fut.result()
        except Exception as exc:  # one bad proposal never stops a run
            return {
                "spec": None,
                "text": None,
                "cost_usd": 0.0,
                "error": f"proposer crash: {type(exc).__name__}: {exc}",
            }

    def finish(self, req, out, result):
        self.inflight = [r for r in self.inflight if r is not req]
        if result is None:
            result = {
                "valid": False,
                "score": -1e6,
                "feasible": False,
                "error": out.get("error"),
                "instances": {},
                "graphs": [],
            }
        extra = {
            "proposer_error": out.get("error"),
            "cost_usd": out.get("cost_usd", 0.0),
            "tokens_in": out.get("tokens_in"),
            "tokens_out": out.get("tokens_out"),
            "llm_seconds": out.get("seconds"),
            "model_text": out.get("text"),
            "model_reasoning": out.get("reasoning"),
            "reasoning_tokens": out.get("reasoning_tokens"),
            "finish_reason": out.get("finish_reason"),
            "cost_source": out.get("cost_source"),
            "repairs_used": out.get("repairs_used"),
            "attempts": out.get("attempts"),
            "batch": self.batches,
            "proposal": req.get("proposal"),
            "explore_p": req.get("explore_p"),
            "focus": (req.get("focus") or {}).get("graph"),
            "tactic": req.get("tactic"),
            "context": req.get("context"),
            **self.store_prompt(out.get("messages")),
        }
        rec, improved = self.add(
            out["spec"], result, req["mode"], req["parents"], req["island"], extra
        )
        self.completed += 1
        if improved:
            self.merge_credit = True
        if self.cfg["engine"] == "adaevolve":
            self.update_island(req["island"], rec)
        self.tactic_outcome(req, rec, improved)
        err = out.get("error") or ""
        if err.startswith("BudgetExhausted"):
            self.stop_reason = "budget exhausted"
        elif err.startswith("RuntimeError: network disabled"):
            self.stop_reason = "network disabled"
        return improved

    def after(self, reqs, improved, propose_seconds, eval_seconds):
        cfg = self.cfg
        self.log_batch(reqs, propose_seconds, eval_seconds)
        self.batches += 1
        self.refresh_report()
        if improved:
            self.since_improvement = 0
        else:
            self.since_improvement += len(reqs)
        engine = cfg["engine"]
        if engine == "adaevolve" and self.completed % cfg["migration_every"] < len(
            reqs
        ):
            self.migrate()
        if engine == "evox":
            self.evox_window(len(reqs))
        elif (
            (cfg["tactics"] or engine in ("adaevolve", "gepa"))
            and self.proposals < cfg["max_proposals"]
            and (self.since_improvement >= cfg["stagnation"] or self.need_tactics)
        ):
            self.need_tactics = False
            self.since_improvement = 0
            self.start_reflection("tactics" if cfg["tactics"] else "insights")

    def run_sync(self, pool, threads):
        cfg = self.cfg
        while self.can_submit():
            reqs = self.plan(min(cfg["batch"], cfg["max_proposals"] - self.proposals))
            start = time.time()
            futures = [self.submit(req, threads) for req in reqs]
            outs = [self.collect(fut) for fut in futures]
            propose_seconds = time.time() - start
            results = self.evaluate_specs([o["spec"] for o in outs], pool)
            eval_seconds = time.time() - start - propose_seconds
            improved = False
            for req, out, result in zip(reqs, outs, results):
                improved |= self.finish(req, out, result)
            self.after(reqs, improved, propose_seconds, eval_seconds)

    def run_async(self, pool, threads):
        """Steady state: refill to `batch` in-flight requests after each return."""
        running = {}
        while True:
            self.poll_reflection()
            while len(running) < self.cfg["batch"] and self.can_submit():
                req = self.plan(1)[0]
                running[self.submit(req, threads)] = req
            if not running:
                break
            waiting = set(running)
            if self.reflection is not None:
                waiting.add(self.reflection[1])
            done, _ = cf.wait(waiting, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                if fut not in running:
                    continue  # the reflection; applied at the top of the loop
                req = running.pop(fut)
                out = self.collect(fut)
                start = time.time()
                result = self.evaluate_specs([out["spec"]], pool)[0]
                improved = self.finish(req, out, result)
                self.after(
                    [req], improved, out.get("seconds") or 0.0, time.time() - start
                )

    def run(self):
        cfg = self.cfg
        self.log(
            "start",
            config=cfg,
            git_commit=_git_commit(),
            evaluator_sha256=evaluator.evaluator_hash(),
        )
        ctx = multiprocessing.get_context("spawn")
        with (
            cf.ProcessPoolExecutor(cfg["eval_workers"], mp_context=ctx) as pool,
            cf.ThreadPoolExecutor(max(1, cfg["batch"])) as threads,
            cf.ThreadPoolExecutor(1) as reflect_pool,
        ):
            self.reflect_pool = reflect_pool
            seed_specs = [json.loads(Path(p).read_text()) for p in cfg["seeds"]]
            for path, spec, result in zip(
                cfg["seeds"], seed_specs, self.evaluate_specs(seed_specs, pool)
            ):
                rec, _ = self.add(spec, result, "seed", [], None, {"source": path})
                if rec["valid"]:
                    for state in self.islands:
                        state["members"].append(rec["id"])
            if self.best() is not None:
                self.window_start = self.best()["score"]
            if cfg["async"]:
                self.run_async(pool, threads)
            else:
                self.run_sync(pool, threads)
            self.poll_reflection(wait=True)
            self.final_heldout(pool)
        return self.summary()

    def refresh_report(self):
        """Rewrite the derived report.html (never an input to anything)."""
        from .report import write_report

        try:
            self._events.flush()
            write_report([self.run_dir], self.run_dir / "report.html")
        except Exception as exc:  # observability must not stop a campaign
            self.log("report_error", error=f"{type(exc).__name__}: {exc}")

    def log_batch(self, reqs, propose_seconds, eval_seconds):
        best = self.best()
        data = {
            "batch": self.batches,
            "proposals": self.proposals,
            "completed": self.completed,
            "inflight": len(self.inflight),
            "requests": [
                {
                    k: r.get(k)
                    for k in (
                        "mode",
                        "parents",
                        "island",
                        "explore_p",
                        "proposal",
                        "tactic",
                    )
                }
                | {"focus": (r.get("focus") or {}).get("graph")}
                for r in reqs
            ],
            "best_id": self.best_id,
            "best_score": best["score"] if best else None,
            "since_improvement": self.since_improvement,
            "propose_seconds": round(propose_seconds, 2),
            "eval_seconds": round(eval_seconds, 2),
            "usage": self.proposer.usage(),
        }
        if self.cfg["engine"] == "adaevolve":
            data["islands"] = [
                {
                    "members": s["members"],
                    "best": self.records[s["members"][0]]["score"]
                    if s["members"]
                    else None,
                    "G": round(s["G"], 6),
                    "visits": round(s["visits"], 4),
                    "reward": round(s["reward"], 6),
                }
                for s in self.islands
            ]
        if self.cfg["engine"] == "gepa":
            data["front"] = self.pareto_front()
            data["merges"] = self.merges
        if self.cfg["engine"] == "evox":
            data["strategy"] = self.strategy
        if self.tactics:
            active = self.active_tactic(promote=False)
            data["active_tactic"] = active["id"] if active else None
        self.log("batch", **data)

    def final_heldout(self, pool):
        """Score the top candidates on held-out graphs. Never fed back."""
        top, seen = [], set()
        for r in self.ranked(r for r in self.records if r["valid"]):
            if r["hash"] not in seen:
                seen.add(r["hash"])
                top.append(r)
            if len(top) >= self.cfg["final_heldout_top"]:
                break
        jobs = [pool.submit(evaluator.evaluate, r["spec"], "heldout") for r in top]
        self.heldout = []
        for r, fut in zip(top, jobs):
            res = fut.result()
            row = {
                "id": r["id"],
                "hash": r["hash"],
                "train_score": r["score"],
                "heldout": res.get("heldout"),
                "feasible_all": res.get("feasible"),
                "graphs": [
                    {
                        k: g.get(k)
                        for k in (
                            "graph",
                            "role",
                            "failures",
                            "incomplete",
                            "value_max",
                            "T",
                            "excess_T",
                            "gap_mean",
                        )
                    }
                    for g in res.get("graphs", [])
                ],
            }
            self.heldout.append(row)
            self.log("heldout", feedback=False, **row)

    def summary(self):
        best = self.best()
        usage = self.proposer.usage()
        valid = [r for r in self.records if r["mode"] != "seed"]
        out = {
            "run_dir": str(self.run_dir),
            "engine": self.cfg["engine"],
            "kinds": self.cfg["kinds"],
            "stop_reason": self.stop_reason,
            "proposals": self.proposals,
            "valid_proposals": sum(1 for r in valid if r["valid"]),
            "invalid_proposals": sum(1 for r in valid if not r["valid"]),
            "seed_best": max(
                (
                    r["score"]
                    for r in self.records
                    if r["mode"] == "seed" and r["valid"]
                ),
                default=None,
            ),
            "best": None
            if best is None
            else {
                "id": best["id"],
                "hash": best["hash"],
                "score": best["score"],
                "feasible_on_train_probes": best["feasible"],
                "spec": best["spec"],
            },
            "heldout": getattr(self, "heldout", []),
            "usage": usage,
            "insights": self.insights,
            "tactics": self.tactics,
            "merges": self.merges,
            "strategy": self.strategy,
            "strategy_history": self.strategy_history,
            "evaluator_sha256": evaluator.evaluator_hash(),
            "wall_seconds": round(time.time() - self.started, 1),
            "claim_scope": "finite probe evidence; not a proof",
        }
        (self.run_dir / "summary.json").write_text(
            json.dumps(out, indent=2, default=str) + "\n"
        )
        if best is not None:
            (self.run_dir / "best.json").write_text(
                json.dumps(best["spec"], indent=2) + "\n"
            )
        self.log("end", stop_reason=self.stop_reason, usage=usage)
        self.refresh_report()
        self._events.close()
        self._tsv.close()
        return out


def default_run_dir(cfg):
    stamp = time.strftime("%y%m%d-%H%M%S")
    digest = hashlib.sha256(canonical_json(cfg).encode()).hexdigest()[:6]
    name = cfg.get("name", "campaign")
    return evaluator.ROOT_DIR / "runs" / f"{name}-{stamp}-{digest}"


def build_proposer(cfg, allow_network, env_file=None):
    provider = cfg.get("provider") or {"type": "offline"}
    if provider["type"] == "offline":
        from .proposers import OfflineMutator

        return OfflineMutator(seed=cfg.get("seed", 0))
    if provider["type"] != "openai_compatible":
        raise ValueError("provider.type must be offline or openai_compatible")
    if not allow_network:
        raise ValueError("live provider requires --allow-network")
    from .llm import client_from_config, load_dotenv
    from .proposers import LLMProposer

    load_dotenv(
        env_file or evaluator.ROOT_DIR / ".env",
        keys={provider.get("api_key_env", "XAI_API_KEY")},
    )
    client = client_from_config(provider, allow_network=True)
    reflector = None
    if cfg.get("reflector"):
        rcfg = cfg["reflector"]
        load_dotenv(
            env_file or evaluator.ROOT_DIR / ".env",
            keys={rcfg.get("api_key_env", "XAI_API_KEY")},
        )
        reflector = client_from_config(rcfg, allow_network=True)
    return LLMProposer(client, reflector, repairs=provider.get("repairs", 1))


def run_campaign(cfg, run_dir=None, allow_network=False, env_file=None):
    if os.environ.get("LRX_FORBID_NETWORK") and allow_network:
        raise RuntimeError("LRX_FORBID_NETWORK is set")
    proposer = build_proposer(cfg, allow_network, env_file)
    campaign = Campaign(cfg, run_dir or default_run_dir(cfg), proposer)
    try:
        return campaign.run()
    except BudgetExhausted as exc:
        campaign.stop_reason = f"budget: {exc}"
        return campaign.summary()
