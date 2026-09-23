"""Constrained policy experiments with bounded work and independently replayed words."""

import hashlib
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .certificates import CertificateValidator
from .evaluate import source_hash
from .state import (
    apply_marked_L,
    apply_marked_R,
    apply_marked_X,
    canonical_root,
    distance_upper_bound,
    is_terminal,
    smaller_root,
    validate_parameters,
    validate_vector,
    vector_from_state,
)

WORK_CAPS = {
    "max_proposals": 100,
    "max_beam_width": 50,
    "max_steps": 5000,
    "max_word_length": 5000,
    "max_total_states": 10_000,
    "max_states_list": 100,
    "max_weight": 1000,
}
DEFAULT_POLICY = {"weights": [3, 3, 2], "beam_width": 10, "max_steps": 300}


def parse_policy(spec):
    if isinstance(spec, str):
        if len(spec) > 8192:
            raise ValueError("Policy JSON too large")
        spec = json.loads(spec)
    if not isinstance(spec, dict) or set(spec) != set(DEFAULT_POLICY):
        raise ValueError("Require exactly weights, beam_width, max_steps")
    weights = spec["weights"]
    if not isinstance(weights, list) or len(weights) != 3:
        raise ValueError("Require three weights")
    if any(type(w) is not int or not 0 <= w <= 1000 for w in weights) or not sum(
        weights
    ):
        raise ValueError("Require nonnegative integer weights, with positive sum")
    for key, cap in [("beam_width", 50), ("max_steps", 5000)]:
        if type(spec[key]) is not int or not 1 <= spec[key] <= cap:
            raise ValueError(f"Invalid {key}")
    return {**spec, "weights": weights.copy()}


def _policy_hash(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()


def _dataset_hash(states):
    return _policy_hash(states)


@dataclass
class Candidate:
    word: str
    m: int
    r: int
    parent_policy: str
    seed: int
    cost: int

    def to_dict(self):
        return asdict(self)

    def hash(self):
        return _policy_hash(self.to_dict())


@dataclass
class EvaluationResult:
    candidate: Candidate
    valid: bool
    terminal: bool
    projection_length: int | None
    budget_excess: int | None
    timestamp: str

    def to_dict(self):
        return asdict(self)


class CandidateEvaluator:
    def __init__(self, m, r, target_distance=None):
        self.validator = CertificateValidator(m, r)
        self.target_distance = target_distance

    def evaluate(self, candidate, start_state=None):
        if (candidate.m, candidate.r) != (self.validator.m, self.validator.r):
            raise ValueError("Candidate parameters differ from evaluator")
        cert = self.validator.replay_word(candidate.word, start_state=start_state)
        return EvaluationResult(
            candidate,
            cert.replay_valid,
            cert.terminal,
            cert.projection_length,
            len(candidate.word) - self.target_distance
            if cert.terminal and self.target_distance is not None
            else None,
            datetime.now(timezone.utc).isoformat(),
        )


def _state_from_visible(v, m, r):
    validate_vector(v, m, r)
    if not r:
        raise ValueError("At least one zero required")
    j = v.index(0)
    return v[:j] + v[j + 1 :], j


def _heuristic(state, target_u, m):
    u, j = state
    return sum(a == b for a, b in zip(u, target_u)) + (len(u) + 1 if j >= m else 0)


def beam_search(m, r, start_state, policy, max_expansions=10_000, metrics=None):
    policy = parse_policy(policy)
    validate_vector(vector_from_state(start_state), m, r)
    if not 1 <= max_expansions <= 10_000 or m + r > 64:
        raise ValueError("Search exceeds input/work caps")
    if metrics is None:
        metrics = {}
    metrics["expansions"] = 0
    if is_terminal(start_state, m, r):
        return ""
    moves = list(zip("LRX", (apply_marked_L, apply_marked_R, apply_marked_X)))
    order = sorted(range(3), key=lambda i: (-policy["weights"][i], i))
    beam, visited = [("", start_state)], {start_state}
    root = smaller_root(m, r)
    for _ in range(policy["max_steps"]):
        children = {}
        for word, state in beam:
            for i in order:
                if metrics["expansions"] >= max_expansions:
                    metrics["reason"] = "work_limit"
                    return "UNSOLVED"
                metrics["expansions"] += 1
                op, move = moves[i]
                target = move(state)
                if target in visited or target in children:
                    continue
                new_word = word + op
                if is_terminal(target, m, r):
                    return new_word
                children[target] = new_word
        if not children:
            break
        ordered = sorted(children, key=lambda state: -_heuristic(state, root, m))
        beam = [(children[state], state) for state in ordered[: policy["beam_width"]]]
        visited.update(state for _, state in beam)
    metrics["reason"] = "beam_or_depth_exhausted"
    return "UNSOLVED"


class OfflinePolicyProposer:
    def __init__(self, seed=42):
        self.seed = seed

    def propose_policy(self, m, r, parent=None, feedback=None, seed=0):
        rng = random.Random(self.seed + seed)
        if parent is None:
            return {
                "weights": [rng.randint(1, 10) for _ in range(3)],
                "beam_width": rng.randint(3, 30),
                "max_steps": rng.randint(20, 300),
            }
        result = parse_policy(parent)
        i = rng.randrange(3)
        result["weights"][i] = max(
            1, min(1000, result["weights"][i] + rng.choice([-2, -1, 1, 2]))
        )
        change = (
            5 if feedback and feedback["result"] != "SOLVED" else rng.choice([-2, 2])
        )
        result["beam_width"] = max(1, min(50, result["beam_width"] + change))
        return result

    def propose(self, m, r, count=5):
        return [self.propose_policy(m, r, seed=i) for i in range(count)]


def run_experiment(
    m,
    r,
    states=None,
    mode="best_of_n",
    proposals=8,
    seed=42,
    output_file=None,
    proposer=None,
    max_work=1_000_000,
):
    validate_parameters(m, r)
    if (
        r < 1
        or m + r > 64
        or mode not in ("baseline", "best_of_n", "sequential", "parallel")
    ):
        raise ValueError("Invalid graph or mode")
    if type(proposals) is not int or not 1 <= proposals <= 100:
        raise ValueError("Require 1..100 proposals")
    if (
        type(seed) is not int
        or type(max_work) is not int
        or not 1 <= max_work <= 10_000_000
    ):
        raise ValueError("Invalid seed/work budget")
    states = [canonical_root(m, r)] if states is None else [tuple(v) for v in states]
    if not 1 <= len(states) <= 100:
        raise ValueError("Require 1..100 states")
    starts = [_state_from_visible(v, m, r) for v in states]
    count = 1 if mode == "baseline" else proposals
    allowance = min(10_000, max_work // (len(states) * count))
    if allowance < 1:
        raise ValueError("Work budget too small")
    proposer = proposer or OfflinePolicyProposer(seed)
    dataset_hash, code_hash = _dataset_hash(states), source_hash()
    config = dict(
        m=m,
        r=r,
        mode=mode,
        proposals=count,
        seed=seed,
        dataset_hash=dataset_hash,
        code_hash=code_hash,
        max_work=max_work,
        proposer=proposer.configuration()
        if hasattr(proposer, "configuration")
        else {"kind": type(proposer).__name__},
    )
    run_id, records, winners = _policy_hash(config), [], []
    begin = time.perf_counter()
    output = open(output_file, "x") if output_file is not None else None

    def score(record):
        return (
            0 if record["result"] == "SOLVED" else 1,
            record["word_length"] if record["word_length"] is not None else 10**9,
        )

    def evaluate(index, attempt, raw, parent):
        record = {
            **config,
            "run_id": run_id,
            "state_index": index,
            "start_visible": states[index],
            "attempt": attempt,
            "seed": seed,
            "parent_hash": _policy_hash(parent) if parent is not None else None,
            "policy": None,
            "word": None,
            "word_length": None,
            "metrics": {},
            "result": "FAILURE",
            "error": None,
        }
        try:
            policy = parse_policy(raw)
        except (ValueError, TypeError):
            record["error"] = "Invalid policy"
            return record
        record["policy"], record["policy_hash"] = policy, _policy_hash(policy)
        word = beam_search(m, r, starts[index], policy, allowance, record["metrics"])
        if word == "UNSOLVED":
            record["result"] = "UNSOLVED"
        else:
            cert = CertificateValidator(m, r).replay_word(word, starts[index])
            if not cert.replay_valid or not cert.terminal:
                raise AssertionError("Candidate word failed independent verification")
            record.update(result="SOLVED", word=word, word_length=len(word))
            record["metrics"].update(
                projection_length=cert.projection_length,
                budget_excess=len(word) - distance_upper_bound(m, r),
            )
        return record

    try:
        for index in range(len(states)):
            archive, attempt = [], 0
            while attempt < count:
                batch = min(4 if mode == "parallel" else 1, count - attempt)
                jobs = []
                for offset in range(batch):
                    eligible = sorted(
                        (a for a in archive if a["policy"] is not None), key=score
                    )[:2]
                    selected = (
                        eligible[offset % len(eligible)]
                        if eligible and mode in ("sequential", "parallel")
                        else None
                    )
                    parent = selected["policy"] if selected else None
                    feedback = (
                        {
                            "result": selected["result"],
                            "metrics": selected["metrics"],
                            "start_visible": states[index],
                        }
                        if selected
                        else {"start_visible": states[index]}
                    )
                    if mode == "baseline":
                        raw = DEFAULT_POLICY
                    elif hasattr(proposer, "propose_policy"):
                        raw = proposer.propose_policy(
                            m,
                            r,
                            parent=parent,
                            feedback=feedback,
                            seed=index * count + attempt + offset,
                        )
                    else:
                        offered = proposer.propose(m, r, count=1)
                        raw = (
                            offered[0]
                            if isinstance(offered, list) and offered
                            else None
                        )
                    jobs.append((index, attempt + offset, raw, parent))
                if mode == "parallel":
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        current = list(pool.map(lambda job: evaluate(*job), jobs))
                else:
                    current = [evaluate(*job) for job in jobs]
                for record in current:
                    records.append(record)
                    archive.append(record)
                    if output is not None:
                        output.write(json.dumps(record, allow_nan=False) + "\n")
                        output.flush()
                attempt += batch
            winners.append(min(archive, key=score))
    finally:
        if output is not None:
            output.close()
    residuals = [
        w["metrics"]["budget_excess"] for w in winners if w["result"] == "SOLVED"
    ]
    return {
        **config,
        "run_id": run_id,
        "total_states": len(states),
        "solved": sum(w["result"] == "SOLVED" for w in winners),
        "unsolved": sum(w["result"] == "UNSOLVED" for w in winners),
        "failures": sum(w["result"] == "FAILURE" for w in winners),
        "covered_within_budget": sum(v <= 0 for v in residuals),
        "worst_finite_budget_excess": max(residuals, default=None),
        "expansions": sum(r["metrics"].get("expansions", 0) for r in records),
        "wall_seconds": time.perf_counter() - begin,
        "results": winners,
        "attempts": len(records),
        "model_usage": proposer.usage() if hasattr(proposer, "usage") else None,
    }
