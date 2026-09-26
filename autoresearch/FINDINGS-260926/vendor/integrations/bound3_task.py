"""Bound-m tree certificates (bound-contract-3): output schema and limits, no scoring.

A candidate's `certify(family)` returns {"tree": NODE, "note"?} with

    NODE = {"j": axis, "t": threshold, "le": NODE, "ge": NODE}                 (split)
         | {"words": [...], "origins"?: [o_0..o_{k-1}], "picks"?: [p_0..p_{k-1}],
            "weights"?: [...]}                                                   (leaf)

A split sends u_j <= t to "le" and u_j >= t+1 to "ge"; the root box is [1, inf)^k.
A leaf's words are literal words on the REFINED base, where block j holds o_j zero
atoms (lrx_m.refine); picks[j] (0 <= picks[j] < o_j, default 0) is the atom of block j
that is stretched by u_j - o_j (the group's refinement, theorem section 3, formula (6)).
The plain bound-contract-2 output {"words": [...], "weights"?} is a single root leaf with
unit origins. Criterion (8) per leaf and the family verdict are in bound3_evaluator.py.
"""
import re

MAX_DEPTH, MAX_LEAVES, MAX_LEAF_WORDS, MAX_THRESHOLD = 6, 32, 32, 12
MAX_LETTERS, MAX_TOTAL_LETTERS, MAX_NOTE = 4000, 256000, 500
WEIGHT = re.compile(r'-?[0-9]{1,40}(/[0-9]{1,40})?')
MAX_WEIGHT_INT = 10 ** 40


def _int(x, lo, hi, what):
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError('%s must be an integer in [%d, %d]' % (what, lo, hi))
    return x


def _weights(ws, n):
    from fractions import Fraction as Fr
    if not isinstance(ws, list) or len(ws) != n or any(type(x) not in (str, int) for x in ws):
        raise ValueError('weights must be a list of rationals, one per word')
    for i, x in enumerate(ws):  # bounded before Fraction: '1e10000000' would stall the parent
        if (abs(x) >= MAX_WEIGHT_INT) if type(x) is int else not WEIGHT.fullmatch(x):
            raise ValueError('weight %d is not p or p/q with at most 40 digits each' % i)
    try:
        ws = [Fr(x) for x in ws]
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError('weights are not rationals: %s' % exc) from None
    if any(x < 0 for x in ws) or sum(ws) != 1:
        raise ValueError('weights are not a probability vector')
    return ws


def _leaf(node, k, budget):
    words = node.get('words')
    if not isinstance(words, list) or not 1 <= len(words) <= MAX_LEAF_WORDS:
        raise ValueError('a leaf needs 1..%d words' % MAX_LEAF_WORDS)
    for i, w in enumerate(words):
        if type(w) is not str or len(w) > MAX_LETTERS or set(w) - set('LRX'):
            raise ValueError('word %d is not a string over L,R,X of length <= %d' % (i, MAX_LETTERS))
        budget[0] -= len(w)
    if budget[0] < 0:
        raise ValueError('more than %d letters in the whole tree' % MAX_TOTAL_LETTERS)
    origins = node.get('origins', [1] * k)
    if not isinstance(origins, list) or len(origins) != k:
        raise ValueError('origins must be a list of k integers')
    origins = [_int(o, 1, MAX_THRESHOLD + 1, 'origin') for o in origins]
    picks = node.get('picks', [0] * k)
    if not isinstance(picks, list) or len(picks) != k:
        raise ValueError('picks must be a list of k integers')
    picks = [_int(p, 0, o - 1, 'pick') for p, o in zip(picks, origins)]
    ws = node.get('weights')
    return {'kind': 'leaf', 'words': list(words), 'origins': origins, 'picks': picks,
            'weights': None if ws is None else _weights(ws, len(words))}


def _node(node, k, depth, budget, count):
    if not isinstance(node, dict):
        raise ValueError('tree node must be an object')
    if 'le' in node or 'ge' in node or 'j' in node or 't' in node:
        if depth >= MAX_DEPTH:
            raise ValueError('tree deeper than %d' % MAX_DEPTH)
        j = _int(node.get('j'), 0, k - 1, 'split axis j')
        t = _int(node.get('t'), 1, MAX_THRESHOLD, 'split threshold t')
        le = _node(node.get('le'), k, depth + 1, budget, count)
        ge = _node(node.get('ge'), k, depth + 1, budget, count)
        return {'kind': 'split', 'axis': j, 'cut': t, 'left': le, 'right': ge}
    count[0] += 1
    if count[0] > MAX_LEAVES:
        raise ValueError('more than %d leaves' % MAX_LEAVES)
    return _leaf(node, k, budget)


def parse_output(out, k):
    """-> (tree in lrx_m.tree_leaves form with normalized leaves, note). Raises ValueError; never repairs."""
    if not isinstance(out, dict):
        raise ValueError('output must be an object')
    if 'tree' in out:
        tree = _node(out['tree'], k, 0, [MAX_TOTAL_LETTERS], [0])
    elif isinstance(out.get('words'), list):  # bound-contract-2 output: one root leaf, unit origins
        tree = _leaf({'words': out['words'], 'weights': out.get('weights')}, k, [MAX_TOTAL_LETTERS])
    else:
        raise ValueError('output must have "tree" or a list "words"')
    note = out.get('note')
    return tree, (note[:MAX_NOTE] if isinstance(note, str) else None)


def pick_indices(origins, picks):
    """Global zero indices (linear order on the refined base) of the stretched atoms."""
    return [sum(origins[:j]) + p for j, p in enumerate(picks)]
