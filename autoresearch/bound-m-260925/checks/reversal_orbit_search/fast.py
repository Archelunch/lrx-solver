"""Faster pool: core-1 snapshots, both final walks per run, fast Lemma 1 pricing (pruning only)."""
import sys
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
from integrations import lrx_m as C


def _grow(cell, c, w, rk, n, lo, hi, ln, side):
    """One insertion sweep. Mutates cell, w. Returns (c, lo, hi)."""
    if side == 'r':
        j = (hi + 1) % n
        e = rk[cell[j]]
        tt, p = 0, hi
        while tt < ln and rk[cell[p]] > e:
            tt += 1
            p = (p - 1) % n
        if tt:
            f, b = (hi - c) % n, (c - hi) % n
            w.append('L' * f if f <= b else 'R' * b)
            w.append('X' + 'RX' * (tt - 1))
            v = cell[j]
            for s in range(tt):
                cell[(j - s) % n] = cell[(j - s - 1) % n]
            cell[(j - tt) % n] = v
            c = (j - tt) % n
        return c, lo, j
    j = (lo - 1) % n
    e = rk[cell[j]]
    tt, p = 0, lo
    while tt < ln and rk[cell[p]] < e:
        tt += 1
        p = (p + 1) % n
    if tt:
        f, b = (j - c) % n, (c - j) % n
        w.append('L' * f if f <= b else 'R' * b)
        w.append('X' + 'LX' * (tt - 1))
        v = cell[j]
        for s in range(tt):
            cell[(j + s) % n] = cell[(j + s + 1) % n]
        cell[(j + tt) % n] = v
        c = (j + tt - 1) % n
    return c, j, hi


def is_sorted(cell, m):
    i = cell.index(1)
    n = len(cell)
    for x in range(1, m):
        if cell[(i + x) % n] != x + 1:
            return False
    return True


def finals(cell, c, n):
    p = cell.index(1)
    return {'R': 'R' * ((c - p) % n), 'L': 'L' * ((p - c) % n)}


def ranks(m, t):
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    return {x: i for i, x in enumerate(order)}


def gen_pool(state, cuts=None, seeds1=None, seeds2=None, sides=('r', 'l'), three=False):
    """-> dict word -> params. Params: (t, [(seed, sweeps|None, side), ...], fin)."""
    n = len(state)
    m = sum(1 for x in state if x)
    out = {}
    cuts = range(m + 1) if cuts is None else cuts
    seeds1 = range(n) if seeds1 is None else seeds1
    seeds2 = range(n) if seeds2 is None else seeds2
    for t in cuts:
        rk = ranks(m, t)
        for s1 in seeds1:
            for d1 in sides:
                cell, c, w = list(state), 0, []
                lo = hi = s1
                side = d1
                for k1 in range(1, n):
                    c, lo, hi = _grow(cell, c, w, rk, n, lo, hi, k1, side)
                    side = 'l' if side == 'r' else 'r'
                    pre = ''.join(w)
                    if is_sorted(cell, m):
                        for fin, tail in finals(cell, c, n).items():
                            out.setdefault(pre + tail, (t, [(s1, k1, d1)], fin))
                        break
                    for s2 in seeds2:
                        for d2 in sides:
                            cl2, c2, w2 = list(cell), c, [pre]
                            lo2 = hi2 = s2
                            sd = d2
                            ln = 1
                            while ln < n and not is_sorted(cl2, m):
                                c2, lo2, hi2 = _grow(cl2, c2, w2, rk, n, lo2, hi2, ln, sd)
                                sd = 'l' if sd == 'r' else 'r'
                                ln += 1
                            if not is_sorted(cl2, m):
                                continue
                            body = ''.join(w2)
                            for fin, tail in finals(cl2, c2, n).items():
                                out.setdefault(body + tail, (t, [(s1, k1, d1), (s2, None, d2)], fin))
    return out


def fast_profile(state, word, picks):
    """(base, beta) as lrx_m.Profile, without its checks (zero-zero swap -> None). Pruning only."""
    n = len(state)
    zid = {}
    a = []
    zi = 0
    for x in state:
        if x == 0:
            a.append(1000 + zi)
            zi += 1
        else:
            a.append(x)
    pb = {1000 + p: j for j, p in enumerate(picks)}
    k = len(picks)
    c = 0
    d = 0
    cz = [0] * k
    A = [0] * k
    q = 0
    sumd = 0
    sumcz = [0] * k
    for ch in word:
        if ch == 'L':
            j = pb.get(a[c])
            d += 1
            if j is not None:
                cz[j] += 1
            c = c + 1 if c + 1 < n else 0
        elif ch == 'R':
            c = c - 1 if c else n - 1
            j = pb.get(a[c])
            d -= 1
            if j is not None:
                cz[j] -= 1
        else:
            c2 = c + 1 if c + 1 < n else 0
            x, y = a[c], a[c2]
            if x >= 1000 and y >= 1000:
                return None
            q += 1
            nxt = [0] * k
            j = pb.get(x)
            if j is not None:
                cz[j] += 1
                A[j] += 1
            else:
                j = pb.get(y)
                if j is not None:
                    A[j] += 1
                    nxt[j] = -1
            sumd += abs(d)
            for i in range(k):
                sumcz[i] += abs(cz[i])
            d, cz = 0, nxt
            a[c], a[c2] = y, x
    sumd += abs(d)
    for i in range(k):
        sumcz[i] += abs(cz[i])
    return q + sumd, tuple(2 * A[i] + sumcz[i] for i in range(k))


def pareto(items):
    """items: [(base, beta, payload)] -> Pareto front sorted by base."""
    best = {}
    for b, bt, p in items:
        if bt not in best or b < best[bt][0]:
            best[bt] = (b, p)
    srt = sorted((b, bt, p) for bt, (b, p) in best.items())
    fr = []
    for b, bt, p in srt:
        if not any(b2 <= b and all(x <= y for x, y in zip(bt2, bt)) for b2, bt2, _ in fr):
            fr.append((b, bt, p))
    return fr


def front_fast(state, pool, picks):
    items = []
    for w in pool:
        r = fast_profile(state, w, picks)
        if r is not None:
            items.append((r[0], r[1], w))
    fr = pareto(items)
    out = []
    for b, bt, w in fr:  # confirm with the trusted Profile
        try:
            p = C.Profile(state, w, picks)
        except C.CheckError:
            continue
        assert p.base == b and tuple(p.beta) == bt, (w, b, bt, p.base, p.beta)
        out.append((b, bt, w))
    return out
