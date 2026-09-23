"""Compact evaluator feedback for proposers (<= ~2000 tokens, bytes/4 estimate).

Only graphs with feedback=True (sanity, train) are included. Held-out results
never pass through this module.
"""

import json

from .candidates import Candidate, run_rules
from .dsl import EvalError, features

MAX_BYTES = 8_000
WORDS_MIN_M = 8
_MOVES = {
    "L": lambda v: v[1:] + v[:1],
    "R": lambda v: v[-1:] + v[:-1],
    "X": lambda v: (v[1], v[0]) + v[2:],
}
_KEEP = (
    "fail_rate",
    "value_max",
    "T",
    "excess_T",
    "radius",
    "gap_mean",
    "gap_max",
    "failures",
    "incomplete",
    "checked",
    "failure_kinds",
)
_FEATURE_KEYS = (
    "inv",
    "cinv",
    "cdes",
    "disp_sum",
    "disp_max",
    "zeros_block",
    "zero_gap_max",
    "pos1",
    "fixed",
)


def _state_note(item, m, r):
    note = {
        k: item[k] for k in ("v", "d", "reason", "value") if item.get(k) is not None
    }
    if "v" in item:
        f = features(item["v"], m, r)
        note["features"] = {k: f[k] for k in _FEATURE_KEYS}
    return note


def _geodesic(v, table):
    """One shortest word from the exact table (greedy; L before R before X)."""
    word, d = [], table.distance(v)
    while d:
        for letter in "LRX":
            u = _MOVES[letter](v)
            if table.distance(u) == d - 1:
                word.append(letter)
                v, d = u, d - 1
                break
        else:
            raise ValueError("distance table has no descending neighbour")
    return "".join(word)


def word_comparison(result, spec, min_m=None, max_steps_listed=20):
    """Controller word next to one optimal word, on the largest-value probe
    of a feedback graph with m >= min_m (rules candidates that solved it)."""
    min_m = WORDS_MIN_M if min_m is None else min_m
    if not spec or spec.get("kind") != "rules" or not result.get("valid"):
        return None
    pick = None
    for g in result.get("graphs", []):
        if not g.get("feedback") or g["m"] < min_m:
            continue
        for item in g.get("largest", [])[:1]:
            key = (item["value"] - g["T"], item["value"])
            if item.get("d") is not None and (pick is None or key > pick[0]):
                pick = (key, g, item)
    if pick is None:
        return None
    from .evaluator import get_table

    _, g, item = pick
    m, r = g["m"], g["r"]
    v = tuple(item["v"])
    table = get_table(m, r)
    word, _ = run_rules(Candidate(spec), v, m, r, 4 * (m + r) ** 2)
    if word is None:
        return None
    uphill, flat = [], 0
    cur, dcur = v, table.distance(v)
    for i, letter in enumerate(word):
        cur = _MOVES[letter](cur)
        dnext = table.distance(cur)
        if dnext > dcur:
            uphill.append(i)
        elif dnext == dcur:
            flat += 1
        dcur = dnext
    return {
        "graph": g["graph"],
        "v": list(v),
        "d": item["d"],
        "T": g["T"],
        "controller_len": len(word),
        "controller_word": word,
        "optimal_word": _geodesic(v, table),
        "controller_uphill_steps": uphill[:max_steps_listed],
        "controller_uphill_total": len(uphill),
        "controller_flat_total": flat,
        "note": "optimal_word is one shortest word from the exact table; "
        "uphill steps (0-based indices into controller_word) move away from the root",
    }


def descent_detail(result, spec, sample=2000, max_examples=3, max_classes=6):
    """Why a potential fails local descent, on its smallest failing graph.

    Samples up to `sample` states (deterministic) and groups the states with
    no neighbour at phi - 1 or lower by which moves are geodesic (exact table)
    and how phi changes along the best geodesic move. Examples list phi and d
    for every neighbour. Feedback graphs only."""
    if not spec or spec.get("kind") != "potential" or not result.get("valid"):
        return None
    failing = [
        g for g in result.get("graphs", []) if g.get("feedback") and g.get("failures")
    ]
    if not failing:
        return None
    import random

    from .evaluator import get_table

    g = min(failing, key=lambda g: (g["n"], g["m"]))
    m, r = g["m"], g["r"]
    table = get_table(m, r)
    ranker = table.ranker
    cand = Candidate(spec)
    root = tuple(range(1, m + 1)) + (0,) * r
    codes = range(ranker.size)
    if ranker.size > sample:
        codes = sorted(random.Random(f"lrx-descent:{m}:{r}").sample(codes, sample))
    classes, examples = {}, []
    no_descent = too_small = 0
    for code in codes:
        v = ranker.vector(ranker.unrank(code))
        if v == root:
            continue
        d = table.dist[code]
        phi = cand.value(v, m, r)
        nbrs = {k: move(v) for k, move in _MOVES.items()}
        nphi = {k: cand.value(u, m, r) for k, u in nbrs.items()}
        if min(nphi.values()) > phi - 1:
            no_descent += 1
            nd = {k: table.distance(u) for k, u in nbrs.items()}
            geo = [k for k in "LRX" if nd[k] == d - 1]
            step = min(nphi[k] - phi for k in geo)
            key = f"geodesic {'/'.join(geo)}; phi change along it {step:+d}"
            classes[key] = classes.get(key, 0) + 1
            if len(examples) < max_examples:
                examples.append(
                    {
                        "v": list(v),
                        "phi": phi,
                        "d": d,
                        "neighbours": {k: {"phi": nphi[k], "d": nd[k]} for k in "LRX"},
                    }
                )
        elif phi < d:
            too_small += 1
    top = sorted(classes.items(), key=lambda kv: -kv[1])[:max_classes]
    return {
        "graph": g["graph"],
        "states_sampled": len(codes),
        "no_descent": no_descent,
        "phi_below_d": too_small,
        "no_descent_classes": dict(top),
        "examples": examples,
        "note": "a valid potential needs, at every non-root state, a move with phi "
        "lower by >= 1; following a geodesic move where phi does not drop is the "
        "usual cause",
    }


def compress(result, max_examples=6, spec=None):
    """Build a compact feedback dict from an evaluator result.

    With a rules spec, also compare its word with an optimal word on the worst
    m >= WORDS_MIN_M feedback probe (`word_vs_optimal`). With a potential spec
    that fails local descent, add `descent_detail`."""
    if not result.get("valid"):
        return {
            "valid": False,
            "error": result.get("error"),
            "score": result.get("score"),
        }
    graphs = [g for g in result.get("graphs", []) if g.get("feedback")]
    out = {
        "valid": True,
        "kind": result.get("kind"),
        "score": result["score"],
        "feasible_on_probes": result.get("feasible"),
        "stopped": result.get("stopped"),
        "graphs": [
            dict(
                {"graph": g["graph"], "score": g["score"]},
                **{k: g[k] for k in _KEEP if g.get(k) not in (None, {}, 0)},
            )
            for g in graphs
        ],
    }
    examples = []
    for g in sorted(graphs, key=lambda g: g["score"]):
        for item in g.get("worst", []):
            if len(examples) < max_examples:
                examples.append(
                    dict(_state_note(item, g["m"], g["r"]), graph=g["graph"])
                )
    if examples:
        out["failures"] = examples
    else:
        largest = []
        for g in sorted(graphs, key=lambda g: -(g.get("excess_T") or -999)):
            for item in g.get("largest", [])[:1]:
                if len(largest) < max_examples // 2:
                    largest.append(
                        dict(_state_note(item, g["m"], g["r"]), graph=g["graph"])
                    )
        if largest:
            out["largest_values"] = largest
    try:
        words = word_comparison(result, spec) if spec else None
    except (EvalError, ValueError, ZeroDivisionError, OverflowError, RecursionError):
        words = None  # auxiliary feedback must never stop a campaign
    if words:
        out["word_vs_optimal"] = words
    try:
        detail = descent_detail(result, spec) if spec else None
    except (
        EvalError,
        ValueError,
        KeyError,
        OSError,
        ZeroDivisionError,
        OverflowError,
        RecursionError,
    ):
        detail = None  # auxiliary feedback must never stop a campaign
    if detail:
        out["descent_detail"] = detail
    while len(json.dumps(out)) > MAX_BYTES:
        if out.get("failures"):
            out["failures"].pop()
        elif out.get("largest_values"):
            out["largest_values"].pop()
        elif out.get("descent_detail", {}).get("examples"):
            out["descent_detail"]["examples"].pop()
        elif out.get("descent_detail"):
            del out["descent_detail"]
        elif out.get("word_vs_optimal"):
            del out["word_vs_optimal"]
        elif len(out["graphs"]) > 1:
            out["graphs"].pop(0)
        else:
            break
    return out


def estimate_tokens(obj):
    return len(json.dumps(obj)) // 4
