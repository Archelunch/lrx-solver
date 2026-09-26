"""k = 3 insertion-core pools with fused Lemma 1 pricing (search side only; pruning only).

Words are the insertion-core words of REVERSAL-ORBIT.md s.2 (core_word), generalized:
  * up to three cores: (seed, sweeps | None, first side, cut); the last core grows until the cycle is sorted;
  * one cut per core (as word_K / sched_word2 in reversal_carry.py): core i sorts into t_i+1..m, zeros, 1..t_i;
  * zfree: absorbing a zero cell does not use up a turn (word_K's core2_canon rule), sides otherwise alternate.
Pricing follows fast_profile (reversal_orbit_search/fast.py) letter by letter, but the state
is copied at branch points so shared prefixes and the two final walks are priced once. Every front word is
re-priced by the trusted lrx_m.Profile with an assert before it is used.
"""
import sys
sys.path.insert(0, '/Users/pavluhin/Documents/Projects/lrx-lab')
from integrations import lrx_m as C

Z = 1000  # zero ids are Z + global zero index


class S:
    __slots__ = ('cell', 'c', 'd', 'q', 'sd', 'cz', 'A', 'scz', 'w', 'bad')

    def copy(self):
        o = S()
        o.cell, o.c, o.d, o.q, o.sd = self.cell[:], self.c, self.d, self.q, self.sd
        o.cz, o.A, o.scz, o.w, o.bad = self.cz[:], self.A[:], self.scz[:], self.w[:], self.bad
        return o


def start(state, k):
    s = S()
    zi = 0
    s.cell = []
    for x in state:
        if x == 0:
            s.cell.append(Z + zi)
            zi += 1
        else:
            s.cell.append(x)
    s.c = s.d = s.q = s.sd = 0
    s.cz, s.A, s.scz, s.w, s.bad = [0] * k, [0] * k, [0] * k, [], False
    return s


class Ctx:
    def __init__(self, state, picks):
        self.state = state
        self.n = len(state)
        self.m = sum(1 for x in state if x)
        self.k = len(picks)
        self.pb = {Z + p: j for j, p in enumerate(picks)}
        self.rks = {}

    def rk(self, t):
        if t not in self.rks:
            m = self.m
            r = {x: i for i, x in enumerate(list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1)))}
            for z in range(self.n - m):
                r[Z + z] = r[0]
            self.rks[t] = r
        return self.rks[t]

    # ---- letters
    def L(self, s, f):
        pb, n, cell = self.pb, self.n, s.cell
        for _ in range(f):
            j = pb.get(cell[s.c])
            s.d += 1
            if j is not None:
                s.cz[j] += 1
            s.c = s.c + 1 if s.c + 1 < n else 0
        s.w.append('L' * f)

    def R(self, s, b):
        pb, n, cell = self.pb, self.n, s.cell
        for _ in range(b):
            s.c = s.c - 1 if s.c else n - 1
            j = pb.get(cell[s.c])
            s.d -= 1
            if j is not None:
                s.cz[j] -= 1
        s.w.append('R' * b)

    def X(self, s):
        n, pb, cell = self.n, self.pb, s.cell
        c = s.c
        c2 = c + 1 if c + 1 < n else 0
        x, y = cell[c], cell[c2]
        if x >= Z and y >= Z:
            s.bad = True
        s.q += 1
        nxt = [0] * self.k
        j = pb.get(x)
        if j is not None:
            s.cz[j] += 1
            s.A[j] += 1
        else:
            j = pb.get(y)
            if j is not None:
                s.A[j] += 1
                nxt[j] = -1
        s.sd += abs(s.d)
        for i in range(self.k):
            s.scz[i] += abs(s.cz[i])
        s.d, s.cz = 0, nxt
        cell[c], cell[c2] = y, x
        s.w.append('X')

    def goto(self, s, p):
        n = self.n
        f, b = (p - s.c) % n, (s.c - p) % n
        if f <= b:
            self.L(s, f)
        else:
            self.R(s, b)

    def grow(self, s, rk, lo, hi, ln, side):
        """One insertion step (as core_word), priced inline. -> (lo, hi, absorbed value)."""
        n, cell = self.n, s.cell
        if side == 'r':
            j = (hi + 1) % n
            v = cell[j]
            e = rk[v]
            tt, p = 0, hi
            while tt < ln and rk[cell[p]] > e:
                tt += 1
                p = (p - 1) % n
            if tt:
                self._block(s, hi, tt, -1)
            return lo, j, v
        j = (lo - 1) % n
        v = cell[j]
        e = rk[v]
        tt, p = 0, lo
        while tt < ln and rk[cell[p]] < e:
            tt += 1
            p = (p + 1) % n
        if tt:
            self._block(s, j, tt, 1)
        return j, hi, v

    def _block(self, s, target, tt, dr):
        """goto(target), then X (RX)^(tt-1) (dr = -1) or X (LX)^(tt-1) (dr = +1), priced letter by letter."""
        n, pb, cell, k = self.n, self.pb, s.cell, self.k
        c, d, q, sd, cz, A, scz = s.c, s.d, s.q, s.sd, s.cz, s.A, s.scz
        czany = any(cz)
        f, b = (target - c) % n, (c - target) % n
        w = s.w
        if f <= b:
            w.append('L' * f)
            for _ in range(f):
                v = cell[c]
                if v >= Z:
                    jj = pb.get(v)
                    if jj is not None:
                        cz[jj] += 1
                        czany = True
                d += 1
                c = c + 1 if c + 1 < n else 0
        else:
            w.append('R' * b)
            for _ in range(b):
                c = c - 1 if c else n - 1
                v = cell[c]
                if v >= Z:
                    jj = pb.get(v)
                    if jj is not None:
                        cz[jj] -= 1
                        czany = True
                d -= 1
        w.append('X' + ('RX' if dr < 0 else 'LX') * (tt - 1))
        for it in range(tt):
            if it:
                if dr < 0:
                    c = c - 1 if c else n - 1
                    v = cell[c]
                    if v >= Z:
                        jj = pb.get(v)
                        if jj is not None:
                            cz[jj] -= 1
                            czany = True
                    d -= 1
                else:
                    v = cell[c]
                    if v >= Z:
                        jj = pb.get(v)
                        if jj is not None:
                            cz[jj] += 1
                            czany = True
                    d += 1
                    c = c + 1 if c + 1 < n else 0
            c2 = c + 1 if c + 1 < n else 0
            x, y = cell[c], cell[c2]
            q += 1
            jy = None
            if x >= Z:
                if y >= Z:
                    s.bad = True
                jj = pb.get(x)
                if jj is not None:
                    cz[jj] += 1
                    A[jj] += 1
                    czany = True
                else:
                    if y >= Z:
                        jy = pb.get(y)
            elif y >= Z:
                jy = pb.get(y)
            if jy is not None:
                A[jy] += 1
            sd += abs(d)
            d = 0
            if czany:
                for i in range(k):
                    scz[i] += abs(cz[i])
                    cz[i] = 0
                czany = False
            if jy is not None:
                cz[jy] = -1
                czany = True
            cell[c], cell[c2] = y, x
        s.c, s.d, s.q, s.sd = c, d, q, sd

    def is_sorted(self, s):
        cell, n = s.cell, self.n
        i = cell.index(1)
        for x in range(1, self.m):
            if cell[(i + x) % n] != x + 1:
                return False
        return True

    def price(self, s):
        return s.q + s.sd + abs(s.d), tuple(2 * s.A[i] + s.scz[i] + abs(s.cz[i]) for i in range(self.k))

    def finish(self, s, emit, params):
        if s.bad:
            return
        p = s.cell.index(1)
        n = self.n
        for fin in 'RL':
            t = s.copy()
            if fin == 'L':
                self.L(t, (p - t.c) % n)
            else:
                self.R(t, (t.c - p) % n)
            b, bt = self.price(t)
            emit(b, bt, t, params + (fin,))


class Front:
    """Best base per beta; words stored only when they improve."""
    def __init__(self):
        self.best = {}

    def emit(self, b, bt, s, params):
        cur = self.best.get(bt)
        if cur is None or b < cur[0]:
            self.best[bt] = (b, ''.join(s.w), params)

    def pareto(self):
        items = sorted((b, bt, w, p) for bt, (b, w, p) in self.best.items())
        fr = []
        for b, bt, w, p in items:
            if not any(b2 <= b and all(x <= y for x, y in zip(bt2, bt)) for b2, bt2, _, _ in fr):
                fr.append((b, bt, w, p))
        return fr


def pool(state, picks, cuts=None, seeds1=None, seeds2=None, seeds3=None, three=False, percore=False,
         zfree=(False,), sides='rl', front=None):
    """Two-core pool (as fast.gen_pool) and optionally a three-core extension and per-core cuts.
    Returns a Front. params = (zfree, [(seed, steps|None, side, cut), ...], fin)."""
    ctx = Ctx(state, picks)
    n, m = ctx.n, ctx.m
    F = front or Front()
    cuts = list(range(m + 1)) if cuts is None else list(cuts)
    seeds1 = range(n) if seeds1 is None else seeds1
    seeds2 = range(n) if seeds2 is None else seeds2
    seeds3 = range(n) if seeds3 is None else seeds3
    for zf in zfree:
        for t1 in cuts:
            rk1 = ctx.rk(t1)
            cuts2 = cuts if percore else [t1]
            for s1 in seeds1:
                for d1 in sides:
                    s = start(state, ctx.k)
                    lo = hi = s1
                    side = d1
                    ln = 1
                    k1 = 0
                    while ln < n:
                        lo, hi, v = ctx.grow(s, rk1, lo, hi, ln, side)
                        ln += 1
                        k1 += 1
                        if not (zf and v >= Z):
                            side = 'l' if side == 'r' else 'r'
                        if s.bad:
                            break
                        if ctx.is_sorted(s):
                            ctx.finish(s, F.emit, (zf, ((s1, k1, d1, t1),)))
                            break
                        c1 = (s1, k1, d1, t1)
                        for t2 in cuts2:
                            rk2 = ctx.rk(t2)
                            for s2 in seeds2:
                                for d2 in sides:
                                    _second(ctx, s, rk2, s2, d2, zf, c1, t2, F, three, seeds3, sides, cuts2)
    return F


def _second(ctx, s0, rk2, s2, d2, zf, c1, t2, F, three, seeds3, sides, cuts3):
    n = ctx.n
    s = s0.copy()
    lo = hi = s2
    side = d2
    ln = 1
    k2 = 0
    while ln < n:
        lo, hi, v = ctx.grow(s, rk2, lo, hi, ln, side)
        ln += 1
        k2 += 1
        if not (zf and v >= Z):
            side = 'l' if side == 'r' else 'r'
        if s.bad:
            return
        if ctx.is_sorted(s):
            ctx.finish(s, F.emit, (zf, (c1, (s2, None, d2, t2))))
            return
        if three:
            c2 = (s2, k2, d2, t2)
            for t3 in cuts3:
                rk3 = ctx.rk(t3)
                for s3 in seeds3:
                    for d3 in sides:
                        _third(ctx, s, rk3, s3, d3, zf, c1, c2, t3, F)


def _third(ctx, s0, rk3, s3, d3, zf, c1, c2, t3, F):
    n = ctx.n
    s = s0.copy()
    lo = hi = s3
    side = d3
    ln = 1
    while ln < n:
        lo, hi, v = ctx.grow(s, rk3, lo, hi, ln, side)
        ln += 1
        if not (zf and v >= Z):
            side = 'l' if side == 'r' else 'r'
        if s.bad:
            return
        if ctx.is_sorted(s):
            ctx.finish(s, F.emit, (zf, (c1, c2, (s3, None, d3, t3))))
            return


def confirm(state, fr, picks):
    """Re-price every front word with the trusted Profile. -> [(base, beta, word, params)]"""
    out = []
    for b, bt, w, p in fr:
        try:
            pr = C.Profile(state, w, picks)
        except C.CheckError:
            continue
        assert pr.base == b and tuple(pr.beta) == bt, (w, b, bt, pr.base, pr.beta)
        out.append((b, bt, w, p))
    return out


def word3(state, cores, fin, zfree=False):
    """Plain generator (no pricing), for re-derivation: cores [(seed, steps|None, side, cut)]."""
    k = sum(1 for x in state if x == 0)
    ctx = Ctx(state, list(range(k)))
    s = start(state, k)
    n = ctx.n
    for seed, steps, side, t in cores:
        rk = ctx.rk(t)
        lo = hi = seed
        ln, cnt = 1, 0
        while ln < n and (not ctx.is_sorted(s) if steps is None else cnt < steps):
            lo, hi, v = ctx.grow(s, rk, lo, hi, ln, side)
            ln += 1
            cnt += 1
            if not (zfree and v >= Z):
                side = 'l' if side == 'r' else 'r'
    if not ctx.is_sorted(s) or s.bad:
        return None
    p = s.cell.index(1)
    if fin == 'L':
        ctx.L(s, (p - s.c) % n)
    else:
        ctx.R(s, (s.c - p) % n)
    return ''.join(s.w)
