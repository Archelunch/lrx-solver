#!/usr/bin/env python3
"""Portable exact lower-bound checker for Lemma 1 pricing functionals, general (m, g), up to two multipliers.

Extends negcert_check.py (kept unchanged) from the fixed functional B + 3 beta_0 at m = 9 {0,4} to

    F_W(w) = wB * B(w) + w0 * beta_0(w) + w1 * beta_1(w),        wB >= 1, w0, w1 >= 0 integers,

over all accepted sorting words w of a state (unit base of (m..1){0,g}, or a refined origin), where
beta_j is Lemma 1's slope of the picked zero of block j.  Rational multipliers l_j = w_j / wB.
Stdlib only, no repository imports, reads only the certificate JSON.

STATEMENT CHECKED FOR A CERTIFICATE
    (a) claim_min is a lower bound: a bounded exhaustive search (A* pruned at f >= claim_min) finds no
        accepted sorting word with F_W < claim_min;
    (b) exactness (optional, 'exact': true): every witness word re-prices (letter-by-letter transcription of
        integrations/lrx_m.Profile) to (B, beta) as stated and to F_W = claim_min;
    (c) root-leaf consequence (kind 'root'): claim_min >= wB (T+1) + s (w0 + w1), T = T_m(m+2), s = m-2.
        A root-leaf mixture (criterion (7)/(8) at the unit origin) needs Bbar < T+1 and betabar_j <= s,
        hence wB Bbar + w0 betabar_0 + w1 betabar_1 < wB (T+1) + s (w0 + w1); F_W is linear in the mixture
        weights, so every mixture has at least claim_min: NO ROOT-LEAF CERTIFICATE.
        (Converse, not needed for the negatives: if no (w0, w1) works, LP duality over the (B, beta) points
        gives a feasible mixture; this file does not claim that direction.)

DEFINITIONS (Profile transcription for picks = one zero per block)
    State v of length n = m + r.  L: v -> (v2..vn, v1); R = L^-1; X swaps v1, v2.  Accepted: the word never
    swaps two zeros and ends at (1..m, 0..0).  Blocks are maximal runs of adjacent zeros of the start state
    (lrx_m.parse_state); picks[j] is one zero of block j.  Segments are the runs of rotations between X
    letters; d = #L - #R; cz_j = net crossings of picked zero j (L off it: +1, R onto it: -1); an X with the
    picked zero j in the cursor cell (ZL) adds +1 to the closing cz_j and one to A_j; an X with it in the next
    cell (LZ) adds one to A_j and starts the next segment with cz_j = -1.
    B = q + sum |d|, beta_j = 2 A_j + sum |cz_j|.

PROOF THAT THE SEARCH IS EXHAUSTIVE (as in negcert_check.py, applied to each picked zero separately)
    Lemma R.  Deleting LR, RL or XX from an accepted sorting word keeps it accepted and sorting and does not
        increase F_W: B does not increase, and for EACH picked zero j the argument of negcert_check.py
        (|a+b| <= |a|+|b|, A_j drops by 0 or 2) shows beta_j does not increase; weights are >= 0.
    Lemma C.  In a reduced word every segment is L^a or R^a, B = length, and for each picked zero j,
        |cz_j| of a segment is paid exactly by per-crossing charges and a closing charge that depend only on
        the segment kind and one flag f_j (f_j = 1 iff cz_j = -1 in an L segment, cz_j <= -1 in an R
        segment, or the segment was opened by an LZ X on zero j).  The context is (kind, f_0, f_1) with kind
        in {S, X, L, R}: 1 + 3 + 4 + 4 = 12 contexts (6 when only one zero is weighted).  The six-case
        table of negcert_check.py applies to each zero independently because the letter sequence is shared
        and each zero's cz_j depends only on it.  Hence F_W = sum of step() costs + final(context), and
        min F_W over reduced words is a shortest path on (vector, context) with nonnegative integer costs.
        Unweighted zeros (weight 0 or not picked) are encoded alike (code ZO).
    Lemma A.  A label partition alpha commutes with step() (step reads only zero codes) and maps roots to
        roots.  PatternTable.verify() checks h(u,c) <= w + h(t,c') on every abstract node and letter and
        h(root, c) <= final(c): h is consistent, hence admissible for concrete nodes.
    Theorem.  A* with a consistent heuristic, pruning every node with g + h >= K, pops every node with
        g + h < K in nondecreasing f order; if no root is reached with total < K, every reduced (hence every
        accepted) sorting word has F_W >= K.  Pruning at K discards only nodes whose every completion costs
        >= K (h admissible).  Resource exhaustion raises INCOMPLETE and never yields a bound.

USAGE
    python3 negcert_general.py CERT.json [CERT2.json ...]
    python3 negcert_general.py --selftest
"""
import argparse
import heapq
import itertools
import json
import random
import sys
import time
from array import array

ZW = (100, 101)          # picked zeros of block 0 / block 1 (weighted); labels < 100
ZO = 110                 # every other zero (weight 0)
S = 0
KS, KX, KL, KR = 0, 1, 2, 3
INF = 65535
CNAME = {}
for _k, _n in enumerate('SXLR'):
    for _f in range(4):
        CNAME[_k * 4 + _f] = _n + '%d%d' % (_f & 1, _f >> 1)


# ------------------------------------------------------------------ definitions (Profile transcription)
def base_vector(labels, mask):
    v = [0] if mask & 1 else []
    for i, x in enumerate(labels, 1):
        v.append(x)
        if (mask >> i) & 1:
            v.append(0)
    return v


def refine(base, origin):
    out, j = [], 0
    for x in base:
        if x == 0:
            out.extend([0] * origin[j])
            j += 1
        else:
            out.append(x)
    assert j == len(origin)
    return out


def budget(m, r):
    """T_m(m+r) = m(m+1)/2 + (r-1)(m-2)."""
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def blocks_of(vec):
    """Global zero indices grouped by gap (lrx_m.parse_state)."""
    blocks, gaps, zi, nl = [], [], 0, 0
    for x in vec:
        if x == 0:
            if gaps and gaps[-1] == nl:
                blocks[-1].append(zi)
            else:
                gaps.append(nl)
                blocks.append([zi])
            zi += 1
        else:
            nl += 1
    return blocks


def is_root(v):
    m = sum(1 for x in v if x != 0)
    return len(v) > m and list(v[:m]) == list(range(1, m + 1)) and all(x == 0 for x in v[m:])


def profile_cost(vec, word, picks=None):
    """(B, beta) of Lemma 1 for picks (default first atom of each block); ValueError if rejected."""
    blocks = blocks_of(vec)
    if picks is None:
        picks = [b[0] for b in blocks]
    pb = {p: j for j, p in enumerate(picks)}
    k = len(blocks)
    a, zi = [], 0
    for x in vec:
        if x == 0:
            a.append(1000 + zi)
            zi += 1
        else:
            a.append(x)
    n = len(a)
    c = q = d = 0
    cz, A, segs = [0] * k, [0] * k, []
    for ch in word:
        if ch == 'L':
            d += 1
            j = pb.get(a[c] - 1000)
            if a[c] >= 1000 and j is not None:
                cz[j] += 1
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            j = pb.get(a[c] - 1000)
            if a[c] >= 1000 and j is not None:
                cz[j] -= 1
        elif ch == 'X':
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x >= 1000 and y >= 1000:
                raise ValueError('word swaps two zeros')
            q += 1
            nxt = [0] * k
            if x >= 1000 and pb.get(x - 1000) is not None:
                j = pb[x - 1000]
                cz[j] += 1
                A[j] += 1
            elif y >= 1000 and pb.get(y - 1000) is not None:
                j = pb[y - 1000]
                A[j] += 1
                nxt[j] = -1
            segs.append((d, cz))
            d, cz = 0, nxt
            a[c], a[c2] = y, x
        else:
            raise ValueError('bad letter %r' % ch)
    segs.append((d, cz))
    fin = [0 if x >= 1000 else x for x in a[c:] + a[:c]]
    if not is_root(fin):
        raise ValueError('word does not sort the state')
    B = q + sum(abs(dd) for dd, _ in segs)
    beta = [2 * A[j] + sum(abs(z[j]) for _, z in segs) for j in range(k)]
    return B, beta


def price(vec, word, W, picks=None):
    B, beta = profile_cost(vec, word, picks)
    return W[0] * B + sum(w * b for w, b in zip(W[1:], beta)), B, beta


# ------------------------------------------------------------------ compressed search model (Lemma C)
def encode(vec, W, picks=None):
    """Zero codes: picked zero of block j -> ZW[j] if W[1+j] > 0, every other zero -> ZO."""
    blocks = blocks_of(vec)
    if picks is None:
        picks = [b[0] for b in blocks]
    code = {}
    for j, p in enumerate(picks):
        if j < 2 and W[1 + j] > 0:
            code[p] = ZW[j]
    out, zi = [], 0
    for x in vec:
        if x == 0:
            out.append(code.get(zi, ZO))
            zi += 1
        else:
            out.append(x)
    return bytes(out)


def contexts(W):
    """Non-start contexts reachable for weights W (flags only for weighted zeros)."""
    fl = [f for f in range(4) if not ((f & 1 and W[1] == 0) or (f & 2 and W[2] == 0))]
    out = [KX * 4 + f for f in fl if f != 3]
    out += [KL * 4 + f for f in fl] + [KR * 4 + f for f in fl]
    return out


def make_step(W):
    wB, w0, w1 = W
    zs = [(0, ZW[0], w0)] if w0 else []
    if w1:
        zs.append((1, ZW[1], w1))

    def step(u, c, ch):
        kind = c >> 2
        cost = wB
        nf = 0
        if ch == 'L':
            if kind == KR:
                return None
            u0 = u[0]
            for j, z, w in zs:
                fj = (c >> j) & 1
                cr = u0 == z
                if fj:                              # X1 / L1: cz = -1 so far
                    if not cr:
                        nf |= 1 << j
                elif cr:                            # S / X0 / L0: charge the crossing
                    cost += w
            return u[1:] + u[:1], KL * 4 + nf, cost
        if ch == 'R':
            if kind == KL:
                return None
            t = u[-1:] + u[:-1]
            t0 = t[0]
            for j, z, w in zs:
                fj = (c >> j) & 1
                cr = t0 == z
                if fj:                              # X1 / R1
                    nf |= 1 << j
                    if cr:
                        cost += w
                elif cr:                            # S / X0 / R0 -> R1, first crossing free
                    nf |= 1 << j
            return t, KR * 4 + nf, cost
        if kind == KX:
            return None
        u0, u1 = u[0], u[1]
        if u0 >= 100 and u1 >= 100:
            return None
        for j, z, w in zs:
            fj = (c >> j) & 1
            a0 = u0 == z
            a1 = u1 == z
            cost += w * ((1 - a0) if fj else a0) + (2 * w if (a0 or a1) else 0)
            if a1:
                nf |= 1 << j
        return bytes([u1, u0]) + u[2:], KX * 4 + nf, cost

    return step


def final_cost(c, W):
    return W[1] * (c & 1) + W[2] * ((c >> 1) & 1)


def roots_of(u0):
    """Encoded roots for an encoded start u0: labels 1..m then any arrangement of its zero codes."""
    zeros = sorted(x for x in u0 if x >= 100)
    m = len(u0) - len(zeros)
    lab = bytes(range(1, m + 1))
    return {lab + bytes(p) for p in set(itertools.permutations(zeros))}


def model_cost(vec, word, W, picks=None):
    step = make_step(W)
    u, c, tot = encode(vec, W, picks), S, 0
    for ch in word:
        s = step(u, c, ch)
        if s is None:
            return None
        u, c, w = s
        tot += w
    return tot + final_cost(c, W), u


# ------------------------------------------------------------------ pattern table (Lemma A)
_INV = {KL: lambda t: t[-1:] + t[:-1], KR: lambda t: t[1:] + t[:1], KX: lambda t: bytes([t[1], t[0]]) + t[2:]}
_LET = {KL: 'L', KR: 'R', KX: 'X'}


class PatternTable:
    """Exact min F_W-to-go in the abstraction alpha (labels -> class codes); built by backward Dijkstra,
    then verified consistent independently of how it was built."""

    def __init__(self, u0, classes, W):
        m = sum(1 for x in u0 if x < 100)
        self.W, self.step = W, make_step(W)
        self.ctx = contexts(W)
        tr = bytearray(range(256))
        for code, labs in enumerate(classes, 1):
            for x in labs:
                tr[x] = code
        if sorted(x for cl in classes for x in cl) != list(range(1, m + 1)):
            raise ValueError('classes must partition 1..m')
        self.tr = bytes(tr)
        self.roots = {g.translate(self.tr) for g in roots_of(u0)}
        idx, vecs = {}, []
        for g in sorted(self.roots):
            idx[g] = len(vecs)
            vecs.append(g)
        i = 0
        while i < len(vecs):
            u = vecs[i]
            i += 1
            for t in (u[1:] + u[:1], u[-1:] + u[:-1], bytes([u[1], u[0]]) + u[2:]):
                if t not in idx:
                    idx[t] = len(vecs)
                    vecs.append(t)
        self.idx, self.vecs, self.N = idx, vecs, len(vecs)
        step, ctx = self.step, self.ctx
        h = array('H', [INF]) * (self.N * 16)
        buckets = {}
        for g in self.roots:
            for c in ctx:
                v = final_cost(c, W)
                h[idx[g] * 16 + c] = v
                buckets.setdefault(v, []).append(idx[g] * 16 + c)
        val = 0
        while buckets:
            b = buckets.pop(val, None)
            while b:
                node = b.pop()
                if h[node] != val:
                    continue
                j, c2 = divmod(node, 16)
                kind = c2 >> 2
                ch = _LET[kind]
                u = _INV[kind](vecs[j])
                ju = idx[u] * 16
                for c in ctx:
                    s = step(u, c, ch)
                    if s is not None and s[1] == c2:
                        w = val + s[2]
                        if w < h[ju + c]:
                            h[ju + c] = w
                            buckets.setdefault(w, []).append(ju + c)
            val += 1
        self.h = h

    def verify(self):
        h, idx, W, step = self.h, self.idx, self.W, self.step
        edges = hmax = 0
        for j, u in enumerate(self.vecs):
            for c in self.ctx:
                hv = h[j * 16 + c]
                if hv >= INF:
                    raise AssertionError('unreached abstract node %r %s' % (u, CNAME[c]))
                hmax = max(hmax, hv)
                if u in self.roots and hv > final_cost(c, W):
                    raise AssertionError('h exceeds final cost at an abstract root')
                for ch in 'LRX':
                    s = step(u, c, ch)
                    if s is None:
                        continue
                    edges += 1
                    if hv > s[2] + h[idx[s[0]] * 16 + s[1]]:
                        raise AssertionError('inconsistent h at %r %s %s' % (u, CNAME[c], ch))
        return self.N * len(self.ctx), edges, hmax

    def value(self, u, c):
        if c == S:
            return 0
        return self.h[self.idx[u.translate(self.tr)] * 16 + c]


def start_bound(u0, tables, W):
    step = make_step(W)
    best = None
    for ch in 'LRX':
        s = step(u0, S, ch)
        if s:
            v = s[2] + max(t.value(s[0], s[1]) for t in tables)
            best = v if best is None else min(best, v)
    return best


# ------------------------------------------------------------------ exact bounded search (Theorem)
class Incomplete(RuntimeError):
    pass


def astar(u0, tables, W, bound=None, node_cap=None, want_word=True, log=None):
    """Min F_W over reduced accepted sorting words from encoded u0.
    bound K: nodes with f >= K are pruned.  Returns (F, word, expanded, stored) with F = None iff no word
    has F_W < K (then F_W >= K is proved).  Raises Incomplete at node_cap."""
    step = make_step(W)
    roots = roots_of(u0)
    tabs = [(t.tr, t.idx, t.h) for t in tables]
    K = bound if bound is not None else 1 << 30

    def H(u, c):
        best = 0
        for tr, idx, h in tabs:
            v = h[idx[u.translate(tr)] * 16 + c]
            if v > best:
                best = v
        return best

    best = {u0 + b'\x00': 0}
    heap = [(0, 0, u0, S)]
    expanded = 0
    t0 = time.time()
    while heap:
        f, g, u, c = heapq.heappop(heap)
        if c == 99:
            word = reconstruct(u0, best, u, g, step, W) if want_word else None
            return g, word, expanded, len(best)
        key = u + bytes([c])
        if best[key] < g:
            continue
        expanded += 1
        if node_cap and expanded > node_cap:
            raise Incomplete('node cap %d reached: INCOMPLETE' % node_cap)
        if log and expanded % 1000000 == 0:
            log('    ... %dM expansions, f=%d, stored %d, %.0f s' % (expanded // 1000000, f, len(best),
                                                                      time.time() - t0))
        if u in roots:
            tot = g + final_cost(c, W)
            if tot < K:
                k2 = u + b'\x63'
                if best.get(k2, 1 << 30) > tot:
                    best[k2] = tot
                    best[u + b'\x62' + bytes([c])] = 0     # remember the closing context
                    heapq.heappush(heap, (tot, tot, u, 99))
        for ch in 'LRX':
            s = step(u, c, ch)
            if s is None:
                continue
            t, c2, w = s
            ng = g + w
            k2 = t + bytes([c2])
            if best.get(k2, 1 << 30) > ng:
                fn = ng + H(t, c2)
                if fn >= K:
                    continue
                best[k2] = ng
                heapq.heappush(heap, (fn, ng, t, c2))
    return None, None, expanded, len(best)


def reconstruct(u0, best, u, g, step, W):
    """Walk back from the terminal through stored g-values (no parent pointers)."""
    c = None
    for cc in range(16):
        if (u + b'\x62' + bytes([cc])) in best and best.get(u + bytes([cc])) == g - final_cost(cc, W):
            c = cc
            break
    word = []
    gv = best[u + bytes([c])]
    while not (u == u0 and c == S):
        kind = c >> 2
        ch = _LET[kind]
        p = _INV[kind](u)
        found = None
        for pc in ([S] if p == u0 else []) + list(range(4, 16)):
            pg = best.get(p + bytes([pc]))
            if pg is None:
                continue
            s = step(p, pc, ch)
            if s is not None and s[1] == c and s[0] == u and pg + s[2] == gv:
                found = (pc, pg)
                break
        if found is None:
            raise AssertionError('reconstruction failed')
        word.append(ch)
        u, c, gv = p, found[0], found[1]
    return ''.join(reversed(word))


def reduce_word(w):
    out = []
    for ch in w:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


# ------------------------------------------------------------------ selftest
def raw_dijkstra(vec, W, picks=None):
    """Independent small-case oracle: Dijkstra over (vector, last letter, raw cz_0, raw cz_1)."""
    u0 = encode(vec, W, picks)
    roots = roots_of(u0)
    wB, w0, w1 = W
    zc = [ZW[0], ZW[1]]
    start = (u0, '', 0, 0)
    dist = {start: 0}
    heap = [(0, u0, '', 0, 0)]
    while heap:
        g, u, last, z0, z1 = heapq.heappop(heap)
        if last == 'END':
            return g
        if dist[(u, last, z0, z1)] < g:
            continue
        succ = []
        if u in roots:
            succ.append((u, 'END', 0, 0, g + w0 * abs(z0) + w1 * abs(z1)))
        if last != 'R':
            succ.append((u[1:] + u[:1], 'L', z0 + (u[0] == zc[0]), z1 + (u[0] == zc[1]), g + wB))
        if last != 'L':
            t = u[-1:] + u[:-1]
            succ.append((t, 'R', z0 - (t[0] == zc[0]), z1 - (t[0] == zc[1]), g + wB))
        if last != 'X' and not (u[0] >= 100 and u[1] >= 100):
            cost = wB
            nz = []
            for j, (z, w) in enumerate(((z0, w0), (z1, w1))):
                e = u[0] == zc[j]
                inv = e or u[1] == zc[j]
                cost += w * abs(z + e) + 2 * w * inv
                nz.append(-1 if u[1] == zc[j] else 0)
            succ.append((bytes([u[1], u[0]]) + u[2:], 'X', nz[0], nz[1], g + cost))
        for t, l, a, b, ng in succ:
            if dist.get((t, l, a, b), 1 << 30) > ng:
                dist[(t, l, a, b)] = ng
                heapq.heappush(heap, (ng, t, l, a, b))
    return None


def _sorter(u):
    """Shortest completion (BFS on encoded vectors)."""
    from collections import deque
    roots = roots_of(u)
    par = {u: None}
    dq = deque([u])
    while dq:
        x = dq.popleft()
        if x in roots:
            out = []
            while par[x] is not None:
                x, ch = par[x]
                out.append(ch)
            return ''.join(reversed(out))
        for ch, t in (('L', x[1:] + x[:1]), ('R', x[-1:] + x[:-1]), ('X', bytes([x[1], x[0]]) + x[2:])):
            if ch == 'X' and x[0] >= 100 and x[1] >= 100:
                continue
            if t not in par:
                par[t] = (x, ch)
                dq.append(t)
    return ''


def _apply(u, w):
    for ch in w:
        if ch == 'L':
            u = u[1:] + u[:1]
        elif ch == 'R':
            u = u[-1:] + u[:-1]
        else:
            if u[0] >= 100 and u[1] >= 100:
                return None
            u = bytes([u[1], u[0]]) + u[2:]
    return u


def selftest(log=print):
    rng = random.Random(20260926)
    ok = True
    Ws = [(1, 3, 0), (1, 0, 2), (2, 3, 1), (1, 1, 1), (3, 4, 5)]
    # 1. random sorting words: model = transcription, reduction never increases F
    n = bad = 0
    for vec in ([0, 5, 4, 0, 3, 2, 1], [0, 6, 5, 4, 0, 3, 2, 1], [0, 0, 5, 4, 3, 0, 2, 1], [3, 0, 1, 0, 2, 0, 4]):
        for _ in range(300):
            W = rng.choice(Ws)
            pre = ''.join(rng.choice('LRXX') for _ in range(rng.randint(0, 30)))
            ue = _apply(encode(vec, (1, 1, 1)), pre)
            if ue is None:
                continue
            w = pre + _sorter(ue)
            try:
                F, B, beta = price(vec, w, W)
            except ValueError:
                continue
            n += 1
            rw = reduce_word(w)
            F2, _, _ = price(vec, rw, W)
            mc = model_cost(vec, rw, W)
            if F2 > F or mc is None or mc[0] != F2:
                bad += 1
                log('MISMATCH', vec, W, w, F, F2, mc)
    ok &= bad == 0
    log('selftest 1: %d random sorting words, reduction never increases F, model = transcription: %s'
        % (n, bad == 0))
    # 2. small exact: table-guided A* = raw Dijkstra; and bounded search agrees at K = F and K = F + 1
    cases = [(5, 1 | 4), (5, 1 | 8), (5, 1 | 16), (6, 1 | 8), (6, 1 | 16), (6, 1 | 4), (6, 4 | 32)]
    n = bad = 0
    for m, mask in cases:
        vec = base_vector(list(range(m, 0, -1)), mask)
        for W in ((1, 3, 0), (1, 0, 3), (2, 3, 1), (1, 2, 2)):
            u0 = encode(vec, W)
            tab = PatternTable(u0, [list(range(m, m // 2, -1)), list(range(m // 2, 0, -1))], W)
            tab.verify()
            F, w, _, _ = astar(u0, [tab], W)
            G = raw_dijkstra(vec, W)
            Fw = price(vec, w, W)[0]
            lo = astar(u0, [tab], W, bound=F)[0] is None
            hi = astar(u0, [tab], W, bound=F + 1)[0] == F
            good = F == G == Fw and lo and hi
            n += 1
            bad += not good
            if not good:
                log('  MISMATCH m=%d mask=%s W=%s: A* %s raw %s word %s bounded %s %s' % (m, bin(mask), W, F, G, Fw, lo, hi))
    ok &= bad == 0
    log('selftest 2: %d small exact cases (A* = raw Dijkstra = witness price; bounded search tight): %s'
        % (n, bad == 0))
    # 3. refined origin (block of 2 zeros), both picks
    vec = [0, 0, 5, 4, 3, 0, 2, 1]
    n = bad = 0
    for picks in ([0, 2], [1, 2]):
        for W in ((1, 2, 0), (1, 0, 2), (1, 1, 1)):
            u0 = encode(vec, W, picks)
            tab = PatternTable(u0, [[5, 4], [3, 2, 1]], W)
            tab.verify()
            F, w, _, _ = astar(u0, [tab], W)
            G = raw_dijkstra(vec, W, picks)
            good = F == G == price(vec, w, W, picks)[0]
            n += 1
            bad += not good
    ok &= bad == 0
    log('selftest 3: %d refined-origin cases (picks first and second atom): %s' % (n, bad == 0))
    # 4. agreement with negcert_check.py semantics on m = 9 {0,4} witness words
    vec = base_vector(list(range(9, 0, -1)), 1 | 16)
    for w, B, beta in (('RXLLLLXLLXLXRRXRXRXLXLXLXRXRXRXRXLXLXLXLXLLLXLXLXRRXLX', 54, [7, 7]),
                       ('XLXLXRRXLXRXRRRXRXRXRRXLXLXLXLXLXRRXRXLXLXRXRXRX', 48, [9, 3])):
        got = profile_cost(vec, w)
        ok &= got == (B, beta) and model_cost(vec, w, (1, 3, 0))[0] == B + 3 * beta[0]
    log('selftest 4: m=9 {0,4} witnesses re-price as in negcert-m9-04.json: %s' % ok)
    return ok


# ------------------------------------------------------------------ certificate
def check_certificate(path, log=print, node_cap=None):
    cert = json.load(open(path))
    t0 = time.time()
    m, labels, mask = cert['m'], cert['labels'], cert['mask']
    W = tuple(cert['weights'])
    origin = cert.get('origin', None)
    picks = cert.get('picks', None)
    vec = base_vector(labels, mask)
    if origin:
        vec = refine(vec, origin)
    r = len(vec) - m
    problems = []
    if vec != cert['base']:
        problems.append('state vector %s != certificate %s' % (vec, cert['base']))
    T, s = budget(m, r), m - 2
    if [T, s] != [cert['T'], cert['s']]:
        problems.append('T, s mismatch')
    K = cert['claim_min']
    log('statement: m=%d state=%s  min over accepted sorting words of %d*B + %d*beta_0 + %d*beta_1 >= %d'
        % (m, vec, W[0], W[1], W[2], K))
    u0 = encode(vec, W, picks)
    tables = []
    for classes in cert['abstractions']:
        t1 = time.time()
        tab = PatternTable(u0, classes, W)
        nodes, edges, hmax = tab.verify()
        tables.append(tab)
        log('pattern table %s: %d abstract vectors, %d nodes, %d edges, consistent; max h %d; bound at start '
            '%d (%.1f s)' % (classes, tab.N, nodes, edges, hmax, start_bound(u0, [tab], W), time.time() - t1))
    t1 = time.time()
    F, word, expanded, stored = astar(u0, tables, W, bound=K, node_cap=node_cap, want_word=True,
                                      log=log)
    if F is None:
        log('bounded A* (prune f >= %d): no sorting word below %d; %d expansions, %d stored (%.1f s)'
            % (K, K, expanded, stored, time.time() - t1))
    else:
        problems.append('found a word with F = %d < claimed %d: %s' % (F, K, word))
    attained = False
    for wit in cert.get('witnesses', []):
        Fw, B, beta = price(vec, wit['word'], W, picks)
        good = [B, beta] == [wit['B'], wit['beta']]
        log('witness %s: B=%d beta=%s F=%d %s' % (wit['word'], B, beta, Fw, 'ok' if good else 'BAD'))
        if not good:
            problems.append('witness mismatch')
        if Fw < K:
            problems.append('witness F %d < claim_min %d' % (Fw, K))
        attained = attained or Fw == K
    if cert.get('exact'):
        if not attained:
            problems.append('exact claimed but no witness attains claim_min %d' % K)
        else:
            log('exact minimum %d (lower bound by search, attained by a witness)' % K)
    if cert.get('kind', 'root') == 'root':
        need = W[0] * (T + 1) + s * (W[1] + W[2])
        verdict = K >= need
        log('root mixture needs Bbar < T+1 = %d and betabar_j <= s = %d, so %d Bbar + %d betabar_0 + %d betabar_1 '
            '< %d; every word, hence every mixture, has >= %d: %s'
            % (T + 1, s, W[0], W[1], W[2], need, K, 'NO ROOT-LEAF CERTIFICATE' if verdict else 'not refuted'))
        from fractions import Fraction
        lpb = Fraction(K - s * (W[1] + W[2]), W[0])
        log('implied lower bound on the root LP value min{Bbar : betabar_j <= s}: (%d - %d*%d)/%d = %s (T+1 = %d)'
            % (K, s, W[1] + W[2], W[0], lpb, T + 1))
        if 'lp_value' in cert and Fraction(cert['lp_value']) != lpb:
            problems.append('lp_value %s != implied bound %s' % (cert['lp_value'], lpb))
        if cert.get('refutes', True) and not verdict:
            problems.append('bound does not refute the root leaf')
    log('total %.1f s' % (time.time() - t0))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('certs', nargs='*')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--node-cap', type=int, default=None)
    a = ap.parse_args()
    ok = True
    if a.selftest:
        ok &= selftest()
    for p in a.certs:
        probs = check_certificate(p, node_cap=a.node_cap)
        for pr in probs:
            print('PROBLEM:', pr)
        ok &= not probs
    if not a.selftest and not a.certs:
        ap.error('give certificates or --selftest')
    print('VERIFIED' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
