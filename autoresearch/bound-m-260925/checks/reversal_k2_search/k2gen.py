"""Generalized insertion-core words for k=2 (search side). Pure stdlib function of the state and parameters."""
import sys
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')
from integrations import lrx_m as C
from integrations.bound_task import make_family


def sides(nl, nr, first, mode):
    """Side sequence with nl left and nr right steps. mode 'a': alternate from `first` while both remain,
import sys; sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab'); sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/bound-m-260925/checks/reversal_orbit_search')  # added when copied from the scratch run directory, which held identical copies of fast.py, gen.py, engine.py, survey.py
    then the rest; mode 'b': the surplus side first, then alternate starting with `first`."""
    out = []
    if mode == 'a':
        s = first
        while nl or nr:
            if s == 'l' and nl:
                out.append('l'); nl -= 1
            elif s == 'r' and nr:
                out.append('r'); nr -= 1
            else:
                out.append('l' if nl else 'r'); nl -= out[-1] == 'l'; nr -= out[-1] == 'r'
            s = 'l' if s == 'r' else 'r'
        return out
    d = nl - nr
    out = ['l'] * d if d > 0 else ['r'] * (-d)
    k = min(nl, nr)
    s = first
    for _ in range(2 * k):
        out.append(s)
        s = 'l' if s == 'r' else 'r'
    return out


def core_word2(state, t, cores, fin):
    """cores: list of (seed, side list) or (seed, None, first) = alternate until cyclically sorted.
    Same physical model and insertion rule as reversal_orbit.core_word."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w = list(state), []
    c = 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    def srt():
        i = cell.index(1)
        return all(cell[(i + x) % n] == x + 1 for x in range(m))

    def step(lo, hi, ln, side):
        nonlocal c
        if side == 'r':
            j = (hi + 1) % n
            s = 0
            while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                s += 1
            if s:
                goto(hi)
                w.append('X' + 'RX' * (s - 1))
                v = cell[j]
                for i in range(s):
                    cell[(j - i) % n] = cell[(j - i - 1) % n]
                cell[(j - s) % n] = v
                c = (j - s) % n
            return lo, j
        j = (lo - 1) % n
        s = 0
        while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
            s += 1
        if s:
            goto(j)
            w.append('X' + 'LX' * (s - 1))
            v = cell[j]
            for i in range(s):
                cell[(j + i) % n] = cell[(j + i + 1) % n]
            cell[(j + s) % n] = v
            c = (j + s - 1) % n
        return j, hi

    for core in cores:
        seed = core[0]
        lo = hi = seed % n
        ln = 1
        if core[1] is not None:
            for sd in core[1]:
                if ln >= n:
                    return None
                lo, hi = step(lo, hi, ln, sd)
                ln += 1
        else:
            sd = core[2]
            while ln < n and not srt():
                lo, hi = step(lo, hi, ln, sd)
                ln += 1
                sd = 'l' if sd == 'r' else 'r'
    if not srt():
        return None
    p = cell.index(1)
    w.append('L' * ((p - c) % n) if fin == 'L' else 'R' * ((c - p) % n))
    return ''.join(w)
