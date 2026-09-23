"""Candidate schema v2: constrained JSON, interpreted by trusted code only.

Kinds:
  radius     {"expr": E(n,m,r)}                 predicts the sorting radius
  bound      {"expr": f(state)}                 claims d(v) <= f(v) per state
  potential  {"expr": phi(state)}               local certificate: phi >= 0 and
                                                every non-root state has a
                                                neighbour with phi <= phi(v)-1.
                                                If that holds on a whole graph,
                                                d(v) <= phi(v) there.
  rules      {"rules": [{"if": E, "do": "L|R|X", "set": {"r0": E}}],
              "default": "L|R|X"}               deterministic sorting controller
  beam       {"expr": h(state), "beam_width": w} beam search on heuristic h

Common optional keys: "name" (<=80 chars), "notes" (<=2000 chars, recorded,
never interpreted). Anything else is rejected.
"""

import hashlib
import json

from .dsl import (
    ACTIONS,
    REGISTERS,
    STATE_VARS,
    DslError,
    Env,
    EvalError,
    compile_expr,
)

KINDS = ("radius", "bound", "potential", "rules", "beam")
RULES_ONLY = {"rot", "steps", "prev", *REGISTERS}
STATE_ONLY_VARS = set(STATE_VARS) - RULES_ONLY
RADIUS_VARS = {"n", "m", "r", "T"}
MAX_RULES = 12
MAX_BEAM = 32
MAX_JSON_BYTES = 16_384


class CandidateError(ValueError):
    pass


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def candidate_hash(spec):
    body = {k: v for k, v in spec.items() if k not in ("name", "notes")}
    return hashlib.sha256(canonical_json(body).encode()).hexdigest()[:16]


class Candidate:
    def __init__(self, spec):
        if isinstance(spec, (str, bytes)):
            if len(spec) > MAX_JSON_BYTES:
                raise CandidateError("candidate JSON too large")
            try:
                spec = json.loads(spec)
            except json.JSONDecodeError as exc:
                raise CandidateError(f"invalid JSON: {exc}") from None
        if not isinstance(spec, dict):
            raise CandidateError("candidate must be a JSON object")
        if len(canonical_json(spec)) > MAX_JSON_BYTES:
            raise CandidateError("candidate JSON too large")
        kind = spec.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:
            raise CandidateError(f"kind must be one of {KINDS}")
        allowed = {"kind", "name", "notes"}
        allowed |= {"rules", "default"} if kind == "rules" else {"expr"}
        if kind == "beam":
            allowed |= {"beam_width"}
        extra = set(spec) - allowed
        if extra:
            raise CandidateError(f"unexpected keys {sorted(extra)}")
        for key, cap in (("name", 80), ("notes", 2000)):
            if key in spec and (not isinstance(spec[key], str) or len(spec[key]) > cap):
                raise CandidateError(f"{key} must be a string of <= {cap} chars")
        self.spec = spec
        self.kind = kind
        self.hash = candidate_hash(spec)
        try:
            self._compile()
        except DslError as exc:
            raise CandidateError(str(exc)) from None
        except (TypeError, KeyError, AttributeError, RecursionError) as exc:
            # Arbitrary model JSON must be rejected, never crash the caller.
            raise CandidateError(
                f"malformed candidate ({type(exc).__name__})"
            ) from None

    def _compile(self):
        spec = self.spec
        if self.kind == "rules":
            rules = spec.get("rules")
            if not isinstance(rules, list) or not 1 <= len(rules) <= MAX_RULES:
                raise CandidateError(f"rules must be a list of 1..{MAX_RULES}")
            default = spec.get("default", "L")
            if not isinstance(default, str) or default not in ACTIONS:
                raise CandidateError("default must be L, R or X")
            compiled = []
            for rule in rules:
                if not isinstance(rule, dict) or set(rule) - {"if", "do", "set"}:
                    raise CandidateError("rule keys are if, do, set")
                if not isinstance(rule.get("do"), str) or rule["do"] not in ACTIONS:
                    raise CandidateError("rule 'do' must be L, R or X")
                cond = compile_expr(rule.get("if", 1))
                sets = rule.get("set", {})
                if not isinstance(sets, dict) or set(sets) - set(REGISTERS):
                    raise CandidateError(f"set keys must be among {REGISTERS}")
                compiled_sets = [(k, compile_expr(e)) for k, e in sorted(sets.items())]
                compiled.append((cond, rule["do"], compiled_sets))
            self.rules = compiled
            self.default = default
            # Without the step counter the controller is a deterministic map on
            # (v, registers, rot, prev), so a repeated tuple proves a loop.
            self.detect_cycles = '"steps"' not in canonical_json(rules)
            return
        if "expr" not in spec:
            raise CandidateError("missing expr")
        allowed = RADIUS_VARS if self.kind == "radius" else STATE_ONLY_VARS
        self.fn = compile_expr(spec["expr"], allowed_vars=allowed)
        if self.kind == "beam":
            width = spec.get("beam_width", 8)
            if type(width) is not int or not 1 <= width <= MAX_BEAM:
                raise CandidateError(f"beam_width must be 1..{MAX_BEAM}")
            self.beam_width = width

    def value(self, v, m, r):
        return self.fn(Env(tuple(v), m, r))

    def radius_value(self, m, r):
        n = m + r
        return self.fn(_ParamEnv({"n": n, "m": m, "r": r, "T": _budget(m, r)}))


class _ParamEnv(dict):
    pass


def _budget(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def _move(v, action):
    if action == "L":
        return v[1:] + v[:1]
    if action == "R":
        return v[-1:] + v[:-1]
    return (v[1], v[0]) + v[2:]


def run_rules(candidate, start, m, r, max_steps):
    """Run a rules controller. Returns (word or None, reason)."""
    root = tuple(range(1, m + 1)) + (0,) * r
    n = m + r
    v = tuple(start)
    regs = {k: 0 for k in REGISTERS}
    rot = steps = prev = 0
    word = []
    seen = set() if candidate.detect_cycles else None
    while v != root:
        if steps >= max_steps:
            return None, f"step cap {max_steps}; first moves {''.join(word[:40])}"
        if seen is not None:
            key = (v, rot, prev, *regs.values())
            if key in seen:
                return None, (
                    f"cycle after {steps} steps; first moves {''.join(word[:40])}"
                )
            seen.add(key)
        env = Env(v, m, r, extra=dict(regs, rot=rot, steps=steps, prev=prev))
        action, sets = candidate.default, ()
        for cond, act, rule_sets in candidate.rules:
            if cond(env):
                action, sets = act, rule_sets
                break
        new_regs = {k: fn(env) for k, fn in sets}
        for k, val in new_regs.items():
            if abs(val) > 10**9:
                raise EvalError("register overflow")
            regs[k] = val
        v = _move(v, action)
        rot = (rot + (1 if action == "L" else -1 if action == "R" else 0)) % n
        prev = ACTIONS[action]
        steps += 1
        word.append(action)
    return "".join(word), "solved"


def run_beam(candidate, start, m, r, max_expansions):
    """Beam search on heuristic h (lower is better). Returns (word or None, reason)."""
    root = tuple(range(1, m + 1)) + (0,) * r
    start = tuple(start)
    if start == root:
        return "", "solved"
    width = candidate.beam_width
    fn = candidate.fn
    parents: dict = {start: None}
    beam = [start]
    expansions = 0
    while beam:
        scored = []
        for v in beam:
            for action in "LRX":
                u = _move(v, action)
                if u in parents:
                    continue
                parents[u] = (v, action)
                if u == root:
                    word = []
                    while parents[u] is not None:
                        u, a = parents[u]
                        word.append(a)
                    return "".join(reversed(word)), "solved"
                expansions += 1
                if expansions > max_expansions:
                    return None, "expansion cap"
                scored.append((fn(Env(u, m, r)), u))
        scored.sort(key=lambda item: item[0])
        beam = [u for _, u in scored[:width]]
    return None, "beam exhausted"
