"""Proposers: offline JSON mutator (deterministic) and LLM chat proposer.

Both return plain dicts. Nothing a proposer returns is executed; it is parsed
by candidates.Candidate and interpreted by the evaluator.
"""

import copy
import json
import random

from . import prompt
from .candidates import (
    RADIUS_VARS,
    STATE_ONLY_VARS,
    Candidate,
    CandidateError,
    canonical_json,
)
from .dsl import REGISTERS, TOKEN_VARS

_ARITH = ["add", "sub", "max", "min"]
_CMP = ["lt", "le", "gt", "ge", "eq", "ne"]
_RULE_VARS = sorted(STATE_ONLY_VARS | {"rot", "steps", "prev", *REGISTERS})
MAX_EDITS = 2


def _mentions(expr, name):
    if expr == name:
        return True
    return isinstance(expr, list) and any(_mentions(e, name) for e in expr)


def _unsorted_only(expr):
    """Conservative syntactic proof that a condition is false when csorted=1."""
    if not isinstance(expr, list) or not expr:
        return False
    if expr in (["not", "csorted"], ["eq", "csorted", 0],
                ["eq", 0, "csorted"], ["ne", "csorted", 1], ["ne", 1, "csorted"]):
        return True
    if expr[0] == "and":
        return any(_unsorted_only(e) for e in expr[1:])
    if expr[0] == "or" and len(expr) > 1:
        return all(_unsorted_only(e) for e in expr[1:])
    return False


def rule_edits(parent, child):
    """Rule-level edit distance: Levenshtein over rules, plus 1 if default differs."""
    a = [canonical_json(x) for x in parent.get("rules", [])]
    b = [canonical_json(x) for x in child.get("rules", [])]
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1] + int(parent.get("default") != child.get("default"))


def edit_violation(parent, child, max_edits=MAX_EDITS):
    """None if child is an allowed edit of a rules parent, else the reason."""
    if parent.get("kind") != "rules" or child.get("kind") != "rules":
        return None
    count = rule_edits(parent, child)
    if count > max_edits:
        return (
            f"edit mode allows at most {max_edits} rule changes; this reply makes "
            f"{count}. Copy the other parent rules exactly"
        )
    kept = {canonical_json(x) for x in child.get("rules", [])}
    for rule in parent.get("rules", []):
        condition = rule.get("if")
        if (_mentions(condition, "csorted") and not _unsorted_only(condition)
                and canonical_json(rule) not in kept):
            return (
                "edit mode must keep the parent's finishing rules (conditions using "
                "csorted that may apply when it is true) unchanged"
            )
    return None


class OfflineMutator:
    """Random structural mutations. A no-API baseline, not a smart proposer."""

    name = "offline"

    def __init__(self, seed=0):
        self.seed = seed

    def usage(self):
        return {"requests": 0, "estimated_usd": 0.0}

    def propose(self, mode, parents, kinds, insights=None, seed=0, context=None):
        rng = random.Random(f"{self.seed}:{seed}")
        base = copy.deepcopy(parents[0][0])
        if mode == "merge" and len(parents) > 1 and base.get("kind") == "rules":
            other = parents[1][0]
            if other.get("kind") == "rules":
                rules = base["rules"][: rng.randint(1, len(base["rules"]))]
                rules += other["rules"][: 12 - len(rules)]
                base["rules"] = rules[:12]
        parent = base
        for _ in range(3 if mode == "explore" else 1):
            base = self._mutate(base, rng)
        if mode == "edit":
            for _ in range(20):
                if edit_violation(parent, base) is None:
                    break
                base = self._mutate(copy.deepcopy(parent), rng)
            else:
                base = copy.deepcopy(parent)
        base["name"] = f"offline-{mode}-{seed}"
        base.pop("notes", None)
        return {"spec": base, "text": None, "error": None, "cost_usd": 0.0}

    def reflect(self, summary, seed=0, task="insights"):
        rng = random.Random(f"reflect:{self.seed}:{seed}")
        tactics = [
            "Prefer R when the target is closer counter-clockwise.",
            "Use registers to remember the current pass direction.",
            "Avoid swaps across the zero block.",
            "Weight cyclic inversions more than displacement.",
        ]
        if task == "tactics":
            data = [{"idea": t, "how": "offline"} for t in rng.sample(tactics, 2)]
        elif task == "strategy":
            data = rng.choice(
                [
                    {"parent": "front", "modes": {"exploit": 2, "explore": 1}},
                    {"parent": "top3", "modes": {"exploit": 1}, "focus": True},
                    {"parent": "best", "modes": {"merge": 1, "exploit": 1}},
                ]
            )
        else:
            return {"text": rng.choice(tactics), "cost_usd": 0.0}
        return {"text": f"```json\n{json.dumps(data)}\n```", "cost_usd": 0.0}

    def _vars(self, kind):
        if kind == "radius":
            return sorted(RADIUS_VARS)
        if kind == "rules":
            return _RULE_VARS
        return sorted(STATE_ONLY_VARS)

    def _random_expr(self, rng, kind, depth=0, token=False):
        pool = self._vars(kind) + (sorted(TOKEN_VARS) if token else [])
        roll = rng.random()
        if depth >= 2 or roll < 0.35:
            return rng.choice(pool) if rng.random() < 0.7 else rng.randint(-3, 8)
        if roll < 0.55:
            return [
                rng.choice(_CMP),
                self._random_expr(rng, kind, depth + 1, token),
                self._random_expr(rng, kind, depth + 1, token),
            ]
        if roll < 0.62 and not token and kind != "radius":
            return ["sum_tokens", self._random_expr(rng, kind, depth + 1, True)]
        if roll < 0.7:
            return [
                "mul",
                rng.randint(1, 4),
                self._random_expr(rng, kind, depth + 1, token),
            ]
        return [
            rng.choice(_ARITH),
            self._random_expr(rng, kind, depth + 1, token),
            self._random_expr(rng, kind, depth + 1, token),
        ]

    def _mutate_expr(self, expr, rng, kind, token=False):
        if isinstance(expr, list) and len(expr) > 1 and rng.random() < 0.7:
            index = rng.randrange(1, len(expr))
            inner_token = token or expr[0].endswith("_tokens")
            expr = list(expr)
            expr[index] = self._mutate_expr(expr[index], rng, kind, inner_token)
            return expr
        if type(expr) is int and rng.random() < 0.6:
            return max(-10_000, min(10_000, expr + rng.choice([-2, -1, 1, 2])))
        choice = rng.random()
        if choice < 0.4:
            return self._random_expr(rng, kind, 1, token)
        if choice < 0.7:
            return [
                rng.choice(["add", "max"]),
                expr,
                self._random_expr(rng, kind, 2, token),
            ]
        return ["mul", rng.randint(1, 3), expr]

    def _mutate(self, spec, rng):
        kind = spec["kind"]
        for _ in range(20):
            trial = copy.deepcopy(spec)
            if kind == "rules":
                rules = trial["rules"]
                op = rng.random()
                if op < 0.5:
                    rule = rng.choice(rules)
                    rule["if"] = self._mutate_expr(rule.get("if", 1), rng, "rules")
                elif op < 0.65:
                    rng.choice(rules)["do"] = rng.choice("LRX")
                elif op < 0.75 and len(rules) > 1:
                    i, j = rng.sample(range(len(rules)), 2)
                    rules[i], rules[j] = rules[j], rules[i]
                elif op < 0.85 and len(rules) < 12:
                    rules.insert(
                        rng.randrange(len(rules) + 1),
                        {
                            "if": self._random_expr(rng, "rules"),
                            "do": rng.choice("LRX"),
                        },
                    )
                elif op < 0.92 and len(rules) > 1:
                    rules.pop(rng.randrange(len(rules)))
                else:
                    trial["default"] = rng.choice("LRX")
            else:
                trial["expr"] = self._mutate_expr(trial["expr"], rng, kind)
                if kind == "beam" and rng.random() < 0.2:
                    trial["beam_width"] = rng.randint(1, 32)
            try:
                Candidate(trial)
                return trial
            except CandidateError:
                continue
        return spec


TASKS = {
    "exploit": "Improve the parent. Make a focused change that fixes the "
    "reported failures or reduces the largest values/gaps.",
    "explore": "Propose a substantially different candidate from the parent "
    "(different idea, not a small tweak). It must still be valid.",
    "merge": "Combine the strengths of the parents into one candidate.",
    "fresh": "Propose a new candidate from scratch.",
    "edit": f"Edit the parent with at most {MAX_EDITS} rule changes (change one "
    "rule's condition, action or register update; insert a rule; delete a rule; "
    "or change the default). Copy every other rule exactly, including the "
    "finishing rules that may apply when csorted is true. Rules explicitly "
    "guarded by csorted == 0 may be edited. Aim the change at the worst "
    "reported states.",
}

REFLECT_SYSTEM = (
    "You are the research lead of an evolutionary search over JSON candidates "
    "for the LRX sorting problem. Read the archive summary and write 3-6 short, "
    "concrete tactics (bullets, <= 150 words total) for the next proposals: "
    "what to try, what to stop doing. No JSON candidate. Do not claim proofs."
)

TACTICS_SYSTEM = (
    "You are the research lead of an evolutionary search over JSON candidates "
    "for the LRX sorting problem. The summary holds the best candidates with "
    "evaluator feedback, the recent attempts (status, score vs parent, notes, "
    "errors) and past tactics with their outcomes (trials, wins = new best "
    "found, score changes). Propose 2-4 NEW tactics that could give a "
    "breakthrough. Each must be a concrete change one proposal can implement "
    "(which rule, condition, register or potential term to change, and why), "
    "not generic advice. Do not repeat tactics that failed. Reply with a short "
    "rationale (<= 80 words), then one JSON array in a ```json block:\n"
    '[{"idea": "...", "how": "...", "target": "reported failure or graph it '
    'should fix", "cautions": "what must stay unchanged"}]\n'
    "No candidate JSON. Do not claim proofs."
)

STRATEGY_SYSTEM = (
    "You tune the search strategy of an evolutionary search over JSON "
    "candidates for the LRX sorting problem (EvoX-style meta-evolution). The "
    "strategy decides how each proposal request is built. The summary holds "
    "the current strategy, earlier strategies with their window scores (J = "
    "relative best-score gain per sqrt(window size); 0 means no gain), a "
    "population summary with outcomes per mode, and the recent attempts. "
    "Propose ONE new strategy likely to end the stagnation; do not repeat a "
    "strategy that scored 0. Reply with a short rationale (<= 80 words), then "
    "one JSON object in a ```json block with these keys:\n"
    '  "parent": "best" | "front" | "top3" | "random"  (archive member to change)\n'
    '  "modes": {"exploit": w, "explore": w, "edit": w, "merge": w}  (weights '
    ">= 0; exploit = focused improvement, explore = substantially different "
    "idea, edit = at most 2 rule changes, merge = combine two Pareto-front "
    "members)\n"
    '  "inspirations": 0..3  (other archive members shown for ideas)\n'
    '  "inspiration_pool": "top" | "random"\n'
    '  "history": 0..8  (recent attempts shown to the proposer)\n'
    '  "focus": true | false  (aim each request at the graph where its parent '
    "lags most)\n"
    '  "tactic": null or one concrete idea (<= 400 characters) given to every '
    "proposal\n"
    "No candidate JSON. Do not claim proofs."
)

REFLECT_SYSTEMS = {
    "insights": REFLECT_SYSTEM,
    "tactics": TACTICS_SYSTEM,
    "strategy": STRATEGY_SYSTEM,
}


class LLMProposer:
    """Chat proposer with a local validity check and a bounded repair turn.

    If the reply has no parseable candidate, or the candidate fails the DSL
    check or uses a kind outside the campaign, the validator's message is sent
    back in the same conversation (up to `repairs` times). Only the syntax is
    checked here; scoring stays in the evaluator.
    """

    name = "llm"

    def __init__(self, client, reflect_client=None, repairs=1):
        self.client = client
        self.reflect_client = reflect_client or client
        self.repairs = repairs

    def usage(self):
        usage = self.client.ledger.snapshot()
        if self.reflect_client is not self.client:
            usage["reflector"] = self.reflect_client.ledger.snapshot()
        return usage

    @staticmethod
    def _check(text, kinds):
        """Return (spec, error). spec is None when unusable."""
        try:
            spec = prompt.extract_candidate(text)
        except ValueError as exc:
            return None, f"parse: {exc}"
        try:
            cand = Candidate(spec)
        except CandidateError as exc:
            return spec, f"invalid candidate: {exc}"
        if kinds and cand.kind not in kinds:
            return spec, f"invalid candidate: kind {cand.kind} not allowed; use {kinds}"
        return spec, None

    def propose(self, mode, parents, kinds, insights=None, seed=0, context=None):
        task = TASKS[mode] + f" (proposal id {seed})"
        msgs = prompt.messages(task, parents, kinds, insights, context)
        out = {
            "spec": None,
            "text": None,
            "error": None,
            "cost_usd": 0.0,
            "prompt_prefix": prompt.prefix_hash(kinds),
            "messages": msgs,
            "attempts": [],
        }
        conversation = list(msgs)
        for attempt in range(self.repairs + 1):
            try:
                reply = self.client.complete(conversation)
            except Exception as exc:  # network/budget errors are recorded
                out["error"] = f"{type(exc).__name__}: {exc}"
                partial = getattr(exc, "partial_reasoning", None)
                if partial:
                    out["reasoning"] = partial[:30_000]
                return out
            spec, error = self._check(reply["text"], kinds)
            edit_error = None
            if error is None and mode == "edit" and parents:
                edit_error = error = edit_violation(parents[0][0], spec)
            out["attempts"].append(
                {
                    "error": error,
                    "cost_usd": reply["cost_usd"],
                    "seconds": reply["seconds"],
                }
            )
            out.update(
                text=reply["text"][:20_000],
                reasoning=(reply.get("reasoning") or "")[:30_000],
                reasoning_tokens=(out.get("reasoning_tokens") or 0)
                + (reply.get("reasoning_tokens") or 0),
                finish_reason=reply.get("finish_reason"),
                cost_usd=round(out["cost_usd"] + reply["cost_usd"], 6),
                cost_source=reply.get("cost_source"),
                tokens_in=(out.get("tokens_in") or 0) + reply["tokens_in"],
                tokens_out=(out.get("tokens_out") or 0) + reply["tokens_out"],
                seconds=round((out.get("seconds") or 0) + reply["seconds"], 2),
                # A valid rewrite that breaks the edit limit must not be scored.
                spec=None if edit_error else spec,
                error=error,
            )
            if error is None:
                break
            conversation = conversation + [
                {"role": "assistant", "content": reply["text"][:20_000]},
                {
                    "role": "user",
                    "content": f"The validator rejected that reply: {error}. "
                    "Fix it and reply with one corrected JSON candidate in a "
                    "```json block, using only operators and variables from the "
                    "reference.",
                },
            ]
        out["repairs_used"] = len(out["attempts"]) - 1
        return out

    def reflect(self, summary, seed=0, task="insights"):
        system = REFLECT_SYSTEMS[task] + "\n\n" + prompt.PROBLEM
        kinds = summary.get("allowed_kinds", prompt.KINDS)
        system += ("\n\nAllowed candidate kinds: " + json.dumps(list(kinds))
                   + ". Every tactic must stay within these kinds. Do not recommend "
                   "switching candidate kind outside this campaign contract.")
        if task != "insights":
            system += "\n\n" + prompt.dsl_reference(kinds)
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(summary)[:40_000]},
        ]
        try:
            reply = self.reflect_client.complete(msgs)
        except Exception as exc:
            return {
                "messages": msgs,
                "text": None,
                "error": f"{type(exc).__name__}: {exc}",
                "cost_usd": 0.0,
            }
        return {
            "messages": msgs,
            "text": reply["text"][:6000],
            "cost_usd": reply["cost_usd"],
            "tokens_in": reply["tokens_in"],
            "tokens_out": reply["tokens_out"],
            "seconds": reply["seconds"],
        }
