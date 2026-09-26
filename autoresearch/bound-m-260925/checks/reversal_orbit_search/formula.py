from local import *
import itertools, sys

def good_rel(labels_fn, mask_fn, m, grid, need_single=True):
    fam = make_family(labels_fn(m), mask_fn(m))
    st = fam['unit_base']; T = fam['budget_unit']; n = len(st); k = fam['k']
    h, q = m // 2, (m - 2) // 4
    out = set()
    for dt, s1, dk, d1, ds2, d2, fin in grid:
        t = q + dt
        if not 0 <= t <= m:
            continue
        w = core_word(st, t, [(s1 % n, h + dk, d1), ((h + ds2) % n, None, d2)], fin)
        if not w:
            continue
        r = fast_profile(st, w, list(range(k)))
        if r and r[0] <= T and max(r[1]) <= m - 2:
            out.add((dt, s1, dk, d1, ds2, d2, fin))
    return out

GRID = list(itertools.product(range(-2, 3), (-1, 0, 1), range(-2, 3), 'lr', range(-1, 5), 'lr', 'RL'))
