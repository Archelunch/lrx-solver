"""Scratch helpers for the carry-across search (offline, stdlib + repo modules)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations import lrx_m as C  # noqa: E402
from integrations.bound3_evaluator import leaf_lp  # noqa: E402
from reversal_midband import sched_word  # noqa: E402


def state(m, g, o=(1, 1)):
    return C.refine(C.base_vector(list(range(m, 0, -1)), 1 | 1 << g), list(o))


def price(st, w, picks=None):
    try:
        p = C.Profile(st, w, picks)
    except C.CheckError:
        return None
    return p.base, tuple(p.beta)


def pareto(items):
    """items: dict key=(B, b0, b1) -> payload. Keep nondominated keys."""
    keys = sorted(items)
    out = []
    for k in keys:
        if not any(all(a <= b for a, b in zip(y, k)) for y in out):
            out.append(k)
    return {k: items[k] for k in out}


def root_lp(m, keys):
    s, T = m - 2, C.budget(m, 2)
    costs = [(k[0], list(k[1:])) for k in keys]
    r = leaf_lp(costs, [(1, None), (1, None)], s, T)
    return r


def trace(st, w):
    """Print cells after every X-sweep (debug)."""
    n = len(st); a = list(st); c = 0; out = []
    for ch in w:
        if ch == 'L': c = (c + 1) % n
        elif ch == 'R': c = (c - 1) % n
        else:
            j = (c + 1) % n; a[c], a[j] = a[j], a[c]
    return a, c
