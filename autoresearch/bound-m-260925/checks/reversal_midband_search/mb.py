"""Middle-band mining toolkit (scratch). Exact tables via mmap; exact pricing oracle over all reduced words."""
import hashlib
import heapq
import json
import mmap
import sys
from fractions import Fraction as Fr
from math import lcm
from pathlib import Path

ROOT = Path('/Users/pavluhin/Documents/Projects/lrx-lab')
sys.path.insert(0, str(ROOT))
from integrations import lrx_m as C  # noqa: E402
from src.lrx.table_bfs import Ranker  # noqa: E402

ZID = C.ZID
DIRS = ['datasets/generated', 'datasets/generated/outer-layer-260925', 'datasets/generated/sort-m9-260925',
        'datasets/generated/m10-r2-260926', 'datasets/generated/m11-260925']
_T = {}


def table_path(m, r):
    for d in DIRS:
        p = ROOT / d / ('dist_m%d_r%d.bin' % (m, r))
        if p.exists():
            return p
    return None


class Tab:
    def __init__(self, m, r, verify=False):
        p = table_path(m, r)
        if p is None:
            raise FileNotFoundError((m, r))
        self.meta = json.loads(p.with_suffix('.json').read_text())
        assert self.meta['complete']
        self.f = open(p, 'rb')
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        if verify:
            h = hashlib.sha256()
            for i in range(0, len(self.mm), 1 << 26):
                h.update(self.mm[i:i + (1 << 26)])
            assert h.hexdigest() == self.meta['table_sha256'], 'hash mismatch'
        self.rk = Ranker(m, r)
        self.m, self.r, self.n = m, r, m + r
        self.path = str(p.relative_to(ROOT))
        self.w = self.rk.weights

    def d(self, v):
        """v: visible vector, zeros may carry ids >= ZID."""
        pos = [0] * self.m
        for i, x in enumerate(v):
            if 0 < x < ZID:
                pos[x - 1] = i
        total = 0
        mask = 0
        for p, w in zip(pos, self.w):
            total += (p - (mask & ((1 << p) - 1)).bit_count()) * w
            mask |= 1 << p
        return self.mm[total]


def tab(m, r):
    if (m, r) not in _T:
        _T[(m, r)] = Tab(m, r) if table_path(m, r) else None
    return _T[(m, r)]


def ids(state):
    out, zi = [], 0
    for x in state:
        if x == 0:
            out.append(ZID + zi)
            zi += 1
        else:
            out.append(x)
    return tuple(out)


def state_0g(m, g, o=(1, 1)):
    return C.refine(C.base_vector(list(range(m, 0, -1)), 1 | 1 << g), list(o))


# ------------------------------------------------------------------ exact pricing oracle
ZB = 100  # zero ids inside the oracle: 100 + global zero index (bytes)


def _enc(state):
    out, zi = [], 0
    for x in state:
        if x == 0:
            out.append(ZB + zi)
            zi += 1
        else:
            out.append(x)
    return bytes(out)


class Dist:
    """d(v) on (m, r) and, when tables exist, d of v with one pick zero doubled (m, r+1) and both (m, r+2)."""
    def __init__(self, m, r, picks):
        self.t0 = tab(m, r)
        self.t1 = tab(m, r + 1)
        self.t2 = tab(m, r + 2) if len(picks) == 2 else None
        self.picks = [ZB + p for p in picks]
        self.m = m
        self.tz = [tab(m, r + z) for z in range(0, 6)]  # multi-stretch tables of one zero

    def dz(self, v, p, z):
        out = bytearray()
        for x in v:
            out.append(x)
            if x == p:
                out.extend([ZB + 50] * z)
        return self._d(self.tz[z], bytes(out))

    def _d(self, t, v):
        pos = [0] * self.m
        for i, x in enumerate(v):
            if x < ZB:
                pos[x - 1] = i
        total = 0
        mask = 0
        for p, w in zip(pos, t.w):
            total += (p - (mask & ((1 << p) - 1)).bit_count()) * w
            mask |= 1 << p
        return t.mm[total]

    def d0(self, v):
        return self._d(self.t0, v)

    def stretch(self, v, js):
        out = bytearray()
        for x in v:
            out.append(x)
            if x in js:
                out.append(ZB + 50)
        return bytes(out)

    def H(self, v, d0, wB, wb):
        """Lower bound on wB*base + sum wb_j*beta_j of any standalone sorting word from v (Lemma 1 lift)."""
        best = wB * d0
        if self.t1 is None or not any(wb):
            return best
        nz = [j for j in range(len(wb)) if wb[j]]
        if len(nz) == 1:  # base + lam*beta_j >= (1-f) d_z + f d_{z+1}, lam = z + f (Lemma 1 lift at z e_j)
            j = nz[0]
            z, rem = divmod(wb[j], wB)
            if z + (rem > 0) < len(self.tz) and self.tz[z + (rem > 0)] is not None:
                dzv = d0 if z == 0 else self.dz(v, self.picks[j], z)
                val = wB * dzv
                if rem:
                    val = (wB - rem) * dzv + rem * self.dz(v, self.picks[j], z + 1)
                return max(best, val)
        ds = [self._d(self.t1, self.stretch(v, {p})) for p in self.picks]
        k = len(ds)
        for order in ([0, 1], [1, 0]) if k == 2 else ([0],):
            left, val = wB, 0
            for j in order:
                c = min(wb[j], left)
                val += c * ds[j]
                left -= c
            val += left * d0
            best = max(best, val)
        if self.t2 is not None and k == 2:
            d2 = self._d(self.t2, self.stretch(v, set(self.picks)))
            c = min(wb[0], wb[1], wB)
            # c*(base+b0+b1) + (wb0-c)... use remaining single stretches greedily
            left, val = wB - c, c * d2
            r0, r1 = wb[0] - c, wb[1] - c
            for j, rj in ((0, r0), (1, r1)):
                cc = min(rj, left)
                val += cc * ds[j]
                left -= cc
            val += left * d0
            best = max(best, val)
        return best


def astar(state, picks, wB, wb, tb=None, bound=None, maxnodes=30_000_000):
    """min over reduced sorting words (no LR/RL/XX, no zero-zero swap) of wB*base + sum wb_j*beta_j (Profile
    semantics, picks = global zero indices). Integer weights. A* with an admissible heuristic (table distance,
    Lemma 1 stretched-table bound, pending-segment bound) and reopening. Returns (cost, word, nodes), or
    (None, None, nodes) when min >= bound."""
    m = sum(1 for x in state if x)
    r = len(state) - m
    k = len(picks)
    DS = Dist(m, r, picks)
    pid = {ZB + p: j for j, p in enumerate(picks)}
    v0 = _enc(state)
    cz0 = (0,) * k

    def keyof(v, last, cz):
        return v + bytes([ord(last) if last else 0] + [c + 128 for c in cz])

    def hval(v, cz):
        d0 = DS.d0(v)
        a = sum(w * max(0, abs(c) - 1) for w, c in zip(wb, cz)) + wB * d0
        b = DS.H(v, d0, wB, wb) - sum(w * abs(c) for w, c in zip(wb, cz))
        return max(a, b), d0

    k0 = keyof(v0, '', cz0)
    best = {k0: 0}
    par = {k0: None}
    cnt = 0
    h0, _ = hval(v0, cz0)
    heap = [(h0, 0, cnt, v0, '', cz0, False)]
    nodes = 0
    while heap:
        f, g, _, v, last, cz, goal = heapq.heappop(heap)
        if bound is not None and f >= bound:
            return None, None, nodes
        key = keyof(v, last, cz)
        if goal:
            w = []
            kk = key
            while par[kk] is not None:
                kk, ch = par[kk]
                w.append(ch)
            return g, ''.join(reversed(w)), nodes
        if best.get(key, 1 << 60) < g:
            continue
        nodes += 1
        if nodes > maxnodes:
            raise RuntimeError('node limit')
        if DS.d0(v) == 0:
            tot = g + sum(w * abs(c) for w, c in zip(wb, cz))
            gk = keyof(v, 'G', cz)
            if best.get(gk, 1 << 60) > tot:
                best[gk] = tot
                par[gk] = (key, '')
                cnt += 1
                heapq.heappush(heap, (tot, tot, cnt, v, 'G', cz, True))
            continue
        children = []
        if last != 'R':
            j = pid.get(v[0])
            ncz = cz if j is None else tuple(c + (i == j) for i, c in enumerate(cz))
            children.append(('L', v[1:] + v[:1], ncz, g + wB))
        if last != 'L':
            j = pid.get(v[-1])
            ncz = cz if j is None else tuple(c - (i == j) for i, c in enumerate(cz))
            children.append(('R', v[-1:] + v[:-1], ncz, g + wB))
        if last != 'X' and not (v[0] >= ZB and v[1] >= ZB):
            jx, jy = pid.get(v[0]), pid.get(v[1])
            add = wB
            for i in range(k):
                c = cz[i] + (i == jx)
                add += wb[i] * (abs(c) + 2 * (i == jx or i == jy))
            ncz = tuple(-(i == jy) for i in range(k))
            children.append(('X', bytes([v[1], v[0]]) + v[2:], ncz, g + add))
        for ch, nv, ncz, ng in children:
            nk = keyof(nv, ch, ncz)
            if best.get(nk, 1 << 60) <= ng:
                continue
            best[nk] = ng
            par[nk] = (key, ch)
            cnt += 1
            hv, _ = hval(nv, ncz)
            heapq.heappush(heap, (ng + hv, ng, cnt, nv, ch, ncz, False))
    return None, None, nodes


# ------------------------------------------------------------------ duals (exact LP)
def leaf_dual(pool, k, s, T, bounded, cap=64):
    """pool: [(B, beta)] at the leaf corner (words at origin = corner). bounded: {j: width}.
    Primal: min avg B - T + sum_b width_j max(0, gbar_j - s) s.t. gbar_u <= s.
    Returns (value, lam) where value = optimum over the pool, lam = dual weights (lam_j <= width_j on bounded
    axes, <= cap on unbounded). Solved as the dual LP with the repo's exact simplex."""
    from integrations.lift_evaluator import simplex
    # variables: pi+ , pi-, lam_0..k-1, slack_w (per word), caps slack per j
    n_w = len(pool)
    nv = 2 + k + n_w + k
    A, b = [], []
    for i, (B, beta) in enumerate(pool):  # pi - lam.beta + sl = B
        row = [0] * nv
        row[0], row[1] = 1, -1
        for j in range(k):
            row[2 + j] = -beta[j]
        row[2 + k + i] = 1
        A.append(row)
        b.append(B)
    for j in range(k):  # lam_j + cs_j = cap_j
        row = [0] * nv
        row[2 + j] = 1
        row[2 + k + n_w + j] = 1
        A.append(row)
        b.append(bounded.get(j, cap))
    c = [0] * nv
    c[0], c[1] = -1, 1
    for j in range(k):
        c[2 + j] = s
    st, x, val = simplex(A, b, c)
    assert st == 'optimal', st
    lam = [x[2 + j] for j in range(k)]
    return -val - T, lam


def column_generation(state, picks, s, T, bounded, tb, seed_pool, log=print, max_iter=40, maxnodes=30_000_000):
    """Exact optimum of criterion (8)'s LHS over ALL reduced words at this origin (leaf corner = origin).
    Returns dict(value_pool, lower_bound, lam, words, iters, nodes)."""
    k = len(picks)
    pool = {}
    for w in seed_pool:
        try:
            p = C.Profile(state, w, picks)
        except C.CheckError:
            continue
        key = (p.base,) + tuple(p.beta)
        if key not in pool or len(w) < len(pool[key]):
            pool[key] = w
    keys = sorted(pool)
    keys = [x for x in keys if not any(y != x and all(a <= b for a, b in zip(y, x)) for y in keys)]
    pool = {x: pool[x] for x in keys}
    log('  seed front %d' % len(pool))
    total_nodes = 0
    lbest = None
    val = None
    for it in range(max_iter):
        items = sorted(pool)
        val, lam = leaf_dual([(x[0], list(x[1:])) for x in items], k, s, T, bounded)
        den = lcm(*[Fr(x).denominator for x in lam]) if lam else 1
        wB = den
        wb = [int(x * den) for x in lam]
        try:
            cost, word, nodes = astar(state, picks, wB, wb, tb, maxnodes=maxnodes)
        except RuntimeError:
            log('  it %d pool=%d value=%s lam=%s: pricing hit the node limit; stopping (not exact)' % (
                it, len(pool), val, [str(x) for x in lam]))
            total_nodes += maxnodes
            break
        total_nodes += nodes
        F = Fr(cost, den)
        lbound = F - s * sum(lam) - T
        lbest = lbound if lbest is None else max(lbest, lbound)
        p = C.Profile(state, word, picks)
        assert wB * p.base + sum(a * b for a, b in zip(wb, p.beta)) == cost, (word, p.base, p.beta, cost)
        log('  it %d pool=%d value=%s lam=%s F=%s LB=%s nodes=%d word B=%d beta=%s' % (
            it, len(pool), val, [str(x) for x in lam], F, lbound, nodes, p.base, p.beta))
        keyw = (p.base,) + tuple(p.beta)
        if lbound >= val or keyw in pool:
            break
        pool[keyw] = word
    return {'value_pool': val, 'lower_bound': lbest, 'lam': [str(x) for x in lam], 'pool': pool,
            'nodes': total_nodes, 'iters': it + 1}


# ------------------------------------------------------------------ shortest words
def shortest_dag(state, tb, limit=5000):
    """Count all shortest words (all have length d) and return up to `limit` of them (lexicographic DFS)."""
    v0 = ids(state)
    d0 = tb.d(v0)
    memo = {}

    def succ(v):
        out = [('L', v[1:] + v[:1]), ('R', v[-1:] + v[:-1])]
        if not (v[0] >= ZID and v[1] >= ZID):
            out.append(('X', (v[1], v[0]) + v[2:]))
        return out

    def count(v, dv):
        if dv == 0:
            return 1
        if v in memo:
            return memo[v]
        tot = 0
        for _, u in succ(v):
            if tb.d(u) == dv - 1:
                tot += count(u, dv - 1)
        memo[v] = tot
        return tot

    total = count(v0, d0)
    words = []

    def walk(v, dv, w):
        if len(words) >= limit:
            return
        if dv == 0:
            words.append(''.join(w))
            return
        for ch, u in sorted(succ(v)):
            if tb.d(u) == dv - 1:
                w.append(ch)
                walk(u, dv - 1, w)
                w.pop()

    walk(v0, d0, [])
    return d0, total, words, len(memo)
