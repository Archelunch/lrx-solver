"""Prompt assembly: static cacheable prefix + dynamic suffix.

The prefix depends only on source constants and the campaign's kinds, so
providers with prefix caching bill it once. Insights text (from reflection or
the orchestrator's prompts/insights.md) goes in the dynamic part.
"""

import hashlib
import json

from .candidates import KINDS, MAX_BEAM, MAX_RULES
from .dsl import MAX_DEPTH, MAX_NODES, OPS, STATE_VARS, TOKEN_VARS

PROBLEM = """\
LRX sorting problem. Vectors are arrangements of the multiset {1..m, 0^r},
n = m + r, positions 0..n-1 on a circle. Moves: L = cyclic left shift
(v[0] goes to the end), R = inverse of L, X = swap positions 0 and 1.
Root (sorted) = (1, 2, ..., m, 0, ..., 0). d(v) = LRX distance from v to root.
Sorting radius E_r(n) = max_v d(v).

Open conjecture (not proved; treat as open): for m >= 8,
  E_r(n) <= T = C(n,2) - (r-1)(r+4)/2 = m(m+1)/2 + (r-1)(m-2)
            = (m-2)n - (m^2-3m-4)/2.
Exact tables show equality or 1 below for every computed m >= 8 case, and the
bound FAILS for m <= 7 (m=7: +1 at every even n). Useful structure from the
working notes: the cost of carrying a token distance k is about 2k (k swaps
interleaved with k rotations) plus about k to return for the next token, so
worst cases spread tokens around the circle; zeros are interchangeable,
which saves X moves among zeros and re-entries into the zero block.

Goal: find explicit, checkable artefacts that explain the bound:
 - rules: a deterministic sorting algorithm whose worst-case word length stays
   <= T for m >= 8 (like bubble sort for n(n-1)/2, but for LRX).
 - potential: a closed-form phi with phi >= 0 and, for every non-root state,
   some neighbour (L, R or X) with phi lower by >= 1. Then d(v) <= phi(v).
   A potential with max phi <= T that holds on all graphs is a proof sketch.
 - bound: a per-state upper bound f(v) >= d(v), as tight as possible.
 - radius: a formula for E_r(n) in n, m, r.
 - beam: a heuristic h for beam search (lower = closer to root).
"""

SCORING = """\
Scoring (deterministic, higher is better, 0 is ideal): per graph,
  -1000 * (failed or unfinished probe states / probes)
  -10 * max(0, max value - T)            (only for m >= 8)
  - mean gap to exact distance            (when a table exists)
Graph scores are averaged over sanity + train graphs. Sanity graphs (m <= 6)
are exhaustive; a single failure there stops evaluation. Failures: bound
f < d; potential phi < 0, no descending neighbour, or phi < d; rules/beam
cannot sort the state within the step cap (4 n^2 steps) or replay mismatch.
All words are replayed independently. Probes are finite evidence only.
"""


def dsl_reference(kinds=KINDS):
    lines = [
        "Candidate = ONE JSON object. Expressions are JSON:",
        '  integer | "variable" | ["op", arg, ...]',
        f"Limits: depth <= {MAX_DEPTH}, nodes <= {MAX_NODES} per expression, "
        "integer constants |c| <= 10000. Booleans are 0/1.",
        "Operators: " + ", ".join(OPS) + ".",
        "  add/max/min/and/or are n-ary; sub/lt/le/gt/ge/eq/ne binary;",
        '  floordiv/mod need a positive divisor; ["if", c, a, b];',
        '  ["at", i] = value at position i mod n; ["pos", t] = position of token t;',
        '  ["dmin_of", t] / ["cw_of", t] / ["ccw_of", t] = distance of token t to its',
        '  target (e.g. ["dmin_of","a"] for the token at position 0; 0 for a zero);',
        '  ["sum_tokens", e] / max_tokens / min_tokens / count_tokens evaluate e',
        "  for each token t = 1..m with token variables bound (no nesting).",
        "State variables:",
    ]
    lines += [f"  {k}: {v}" for k, v in STATE_VARS.items()]
    lines.append("Token variables (inside *_tokens only):")
    lines += [f"  {k}: {v}" for k, v in TOKEN_VARS.items()]
    shapes = {
        "radius": '{"kind":"radius","expr":E}   variables n, m, r, T only',
        "bound": '{"kind":"bound","expr":E}',
        "potential": '{"kind":"potential","expr":E}',
        "rules": (
            '{"kind":"rules","rules":[{"if":E,"do":"L|R|X","set":{"r0":E}}],'
            f'"default":"L|R|X"}}   first matching rule fires; <= {MAX_RULES} rules;'
            " rot/steps/prev/r0..r3 are available; the run stops at the root"
        ),
        "beam": f'{{"kind":"beam","expr":E,"beam_width":1..{MAX_BEAM}}}',
    }
    lines.append('Candidate shapes (optional "name" and "notes" strings allowed):')
    lines += [f"  {shapes[k]}" for k in kinds]
    return "\n".join(lines)


MISTAKES = """\
Common mistakes (all rejected by the validator):
 - token variables (t, p, tgt, cw, ccw, dmin, at_tgt, gap_next, zeros_next) are
   NOT operators and only exist inside ["sum_tokens", ...] etc.; for one
   specific token use ["dmin_of", t], ["cw_of", t], ["ccw_of", t];
 - "do" must be the literal "L", "R" or "X" (no expressions); "set" belongs
   inside a rule; registers are r0..r3 only;
 - sub/lt/le/gt/ge/eq/ne take exactly 2 arguments; max_tokens etc. take 1;
 - keep expressions short: nest at most 3-4 levels, reuse registers instead."""

EXAMPLES = {
    "rules": [
        '{"kind":"rules","rules":[\n'
        '   {"if":"csorted","do":"L"},\n'
        '   {"if":["and",["ne","rot",["sub","n",1]],["gt","a","b"],["gt","b",0]],"do":"X"}],\n'
        '  "default":"L"}',
        '{"kind":"rules","rules":[\n'
        '   {"if":["eq","r0",0],"do":"L","set":{"r0":["max_tokens","dmin"]}},\n'
        '   {"if":["gt","r0",0],"do":"R","set":{"r0":["sub","r0",1]}}],\n'
        '  "default":"L"}',
    ],
    "potential": [
        '{"kind":"potential","expr":["add",["sum_tokens",["mul",2,"dmin"]],"cinv"]}'
    ],
    "bound": [
        '{"kind":"bound","expr":["min","T",["add","disp_sum",["mul",2,"cinv"]]]}'
    ],
    "radius": ['{"kind":"radius","expr":["floordiv",["mul","n",["sub","n",1]],2]}'],
    "beam": ['{"kind":"beam","expr":["add","disp_sum","cinv"],"beam_width":8}'],
}


def examples(kinds):
    shown = [e for k in kinds for e in EXAMPLES.get(k, [])]
    return (
        MISTAKES
        + "\nValid examples:\n "
        + "\n ".join(shown)
        + "\n(The examples show syntax only; they are not good candidates.)"
    )


OUTPUT = """\
Reply with a short rationale (<= 120 words), then exactly one JSON candidate
inside a ```json fenced block. No other code. Put your reasoning summary in
the candidate's "notes" field so it is recorded with the result.
"""


def system_prompt(kinds):
    return "\n\n".join(
        [PROBLEM, SCORING, dsl_reference(kinds), examples(kinds), OUTPUT]
    )


def prefix_hash(kinds):
    return hashlib.sha256(system_prompt(kinds).encode()).hexdigest()[:16]


MAX_CONTEXT_CHARS = 8000


def _lines(items):
    text = ""
    for item in items:
        line = json.dumps(item)
        if len(text) + len(line) > MAX_CONTEXT_CHARS:
            break
        text += line + "\n"
    return text.rstrip()


def user_prompt(task, parents, insights=None, kinds=None, context=None):
    """task: short instruction string; parents: list of (spec, feedback) pairs.

    context (optional): tactic {idea, how, target, cautions}, focus {graph,
    parent_score, archive_best}, inspirations [archive members], history
    [recent attempts, newest first]."""
    context = context or {}
    parts = [f"Task: {task}"]
    if kinds:
        parts.append(f"Allowed kinds: {', '.join(kinds)}.")
    tactic = context.get("tactic")
    if tactic:
        lines = [f"BREAKTHROUGH IDEA - IMPLEMENT THIS: {tactic['idea']}"]
        lines += [
            f"{key.capitalize()}: {tactic[key]}"
            for key in ("how", "target", "cautions")
            if tactic.get(key)
        ]
        parts.append("\n".join(lines))
    focus = context.get("focus")
    if focus:
        if "parent_failures" in focus:
            where = (
                f"parent has {focus['parent_failures']} failing states there, "
                f"fewest in the archive {focus['archive_fewest']}"
            )
        else:
            where = (
                f"parent score there {focus['parent_score']}, best in the archive "
                f"{focus['archive_best']}"
            )
        parts.append(
            f"Focus graph: {focus['graph']} ({where}). Aim the change at this "
            "graph's reported states and keep the other graphs from getting worse."
        )
    if insights:
        parts.append("Insights so far:\n" + insights.strip()[:4000])
    for index, (spec, fb) in enumerate(parents, 1):
        parts.append(
            f"Parent {index}:\n```json\n{json.dumps(spec)}\n```\n"
            f"Evaluator feedback {index}:\n{json.dumps(fb)}"
        )
    if context.get("inspirations"):
        parts.append(
            "Other archive members (ideas to borrow; same score scale, higher is "
            "better):\n" + _lines(context["inspirations"])
        )
    if context.get("history"):
        parts.append(
            "Recent attempts, newest first (status keep = new best; score and "
            "parent_score show the change; do not repeat what failed):\n"
            + _lines(context["history"])
        )
    return "\n\n".join(parts)


def messages(task, parents, kinds, insights=None, context=None):
    return [
        {"role": "system", "content": system_prompt(kinds)},
        {
            "role": "user",
            "content": user_prompt(task, parents, insights, kinds, context),
        },
    ]


def extract_candidate(text):
    """Pull the last ```json block (or first bare object) out of model text."""
    if not isinstance(text, str):
        raise ValueError("model text must be a string")
    blocks = text.split("```json")
    decoder = json.JSONDecoder()
    candidates = []
    first_error = None
    for block in blocks[1:]:
        body = block.split("```", 1)[0].strip()
        try:
            candidates.append(json.loads(body))
        except json.JSONDecodeError as exc:
            if first_error is None:
                snippet = body[max(0, exc.pos - 60) : exc.pos + 20]
                first_error = (
                    f"invalid JSON ({exc.msg} at char {exc.pos}, near {snippet!r})"
                )
    if candidates:
        return candidates[-1]
    if first_error:
        raise ValueError(first_error)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model text")
    try:
        value, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError:
        raise ValueError("invalid JSON in model text") from None
    return value
