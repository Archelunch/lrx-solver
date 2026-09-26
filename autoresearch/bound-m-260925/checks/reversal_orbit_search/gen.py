import sys, time, itertools
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
from fractions import Fraction as Fr
from integrations import lrx_m as C
from integrations.bound_task import make_family
from integrations.lift_evaluator import mixture_lp, gap_lp


def core_word(state, t, cores, fin):
    """state: base vector. t: target cut (linear target order t+1..m, zeros, 1..t).
    cores: list of (seed, sweeps or None, first side 'r'/'l'). fin: 'R'|'L'|'S' final walk to label 1.
    Returns word or None if not sorted after the cores."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell = list(state)
    c = 0
    w = []

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        if f <= b:
            w.append('L' * f)
        else:
            w.append('R' * b)
        c = p

    def sorted_cyc():
        i = cell.index(1)
        v = cell[i:] + cell[:i]
        return v[:m] == list(range(1, m + 1))

    for seed, sweeps, side in cores:
        lo = hi = seed
        ln = 1
        cnt = 0
        while ln < n and (sweeps is None and not sorted_cyc() or sweeps is not None and cnt < sweeps):
            if side == 'r':
                j = (hi + 1) % n
                e = rk[cell[j]]
                tt = 0
                p = hi
                while tt < ln and rk[cell[p]] > e:
                    tt += 1
                    p = (p - 1) % n
                if tt:
                    goto(hi)
                    w.append('X' + 'RX' * (tt - 1))
                    v = cell[j]
                    for s in range(tt):
                        a = (j - s) % n
                        b = (j - s - 1) % n
                        cell[a] = cell[b]
                    cell[(j - tt) % n] = v
                    c = (j - tt) % n
                hi = j
            else:
                j = (lo - 1) % n
                e = rk[cell[j]]
                tt = 0
                p = lo
                while tt < ln and rk[cell[p]] < e:
                    tt += 1
                    p = (p + 1) % n
                if tt:
                    goto(j)
                    w.append('X' + 'LX' * (tt - 1))
                    v = cell[j]
                    for s in range(tt):
                        cell[(j + s) % n] = cell[(j + s + 1) % n]
                    cell[(j + tt) % n] = v
                    c = (j + tt - 1) % n
                lo = j
            ln += 1
            cnt += 1
            side = 'l' if side == 'r' else 'r'
    if not sorted_cyc():
        return None
    p = cell.index(1)
    f, b = (p - c) % n, (c - p) % n
    if fin == 'L' or (fin == 'S' and f <= b):
        w.append('L' * f)
    else:
        w.append('R' * b)
    return ''.join(w)


def pool_words(state, max_cores=2, seeds=None, cuts=None):
    n = len(state)
    m = sum(1 for x in state if x)
    seeds = range(n) if seeds is None else seeds
    cuts = range(m + 1) if cuts is None else cuts
    out = set()
    for t in cuts:
        for s1 in seeds:
            for d1 in 'rl':
                for fin in 'RL':
                    w = core_word(state, t, [(s1, None, d1)], fin)
                    if w:
                        out.add(w)
                if max_cores < 2:
                    continue
                for k1 in range(1, n - 1):
                    for s2 in range(n):
                        for d2 in 'rl':
                            for fin in 'RL':
                                w = core_word(state, t, [(s1, k1, d1), (s2, None, d2)], fin)
                                if w:
                                    out.add(w)
    return out


def profiles(state, words):
    """-> dict (base, beta tuple) -> word, pruned to Pareto front."""
    best = {}
    for w in words:
        try:
            p = C.Profile(state, w)
        except C.CheckError:
            continue
        key = tuple(p.beta)
        if key not in best or p.base < best[key][0]:
            best[key] = (p.base, w)
    items = sorted((b, bt, w) for bt, (b, w) in best.items())
    front = []
    for b, bt, w in items:
        if not any(b2 <= b and all(x <= y for x, y in zip(bt2, bt)) for b2, bt2, _ in front):
            front.append((b, bt, w))
    return front


def lp(front, k, s, T):
    costs = [(b, list(bt)) for b, bt, _ in front]
    w, B, sl, t = mixture_lp(costs, k, s)
    g, gw, gB, gs = gap_lp(costs, k, s, T + 1)
    return w, B, sl, t, g
