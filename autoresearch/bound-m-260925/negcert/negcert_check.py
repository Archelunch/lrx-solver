#!/usr/bin/env python3
"""Portable exact lower-bound checker for a Lemma 1 pricing functional (stdlib only, no repository imports).

STATEMENT (m = 9, zeros in gaps {0,4}, the certificate negcert-m9-04.json)
    Unit base v = (0,9,8,7,6,0,5,4,3,2,1): labels 9..1, one zero in gap 0 and one in gap 4.
    For every word w over {L,R,X} that sorts v and is accepted by the Lemma 1 bookkeeping below,
        B(w) + 3 * beta_0(w) >= 75,
    and 75 is attained.  T = T_9(11) = 45 + 1*7 = 52, slope bound s = m-2 = 7.  A root-leaf mixture
    (criterion (7)/(8) at the unit origin) needs Bbar < T+1 = 53 and betabar_0 <= 7, i.e.
    Bbar + 3 betabar_0 < 74.  The functional is linear in the mixture weights, so every mixture has
    Bbar + 3 betabar_0 >= 75: no root-leaf certificate exists for this family.

DEFINITIONS (a transcription of integrations/lrx_m.Profile for a unit state; compare with the group's Lemma 1)
    State: visible vector v of length n = m + r; labels 1..m, r zeros.  L: v -> (v2..vn, v1); R = L^-1;
    X swaps v1, v2.  A word is accepted only if it never swaps two zeros and ends at (1..m, 0..0).
    Zero atoms are distinguishable (tracked by identity); zero 0 is the first zero of the base vector.
    Bookkeeping (cursor model: fixed cells, cursor c, L: c+1, R: c-1, X swaps cells c, c+1):
        segments are the maximal runs of rotations between consecutive X letters (q X letters give q+1
        segments).  In each segment:  d = #L - #R;  cz = net number of times the cursor crosses zero 0:
        L executed while the cursor cell holds zero 0 adds +1; R that brings the cursor onto zero 0 adds -1.
        An X with zero 0 in the cursor cell ("ZL" swap) adds +1 to the cz of the segment it closes and
        counts once in A_0.  An X with zero 0 in the next cell ("LZ" swap) counts once in A_0 and starts
        the next segment with cz = -1.
        B = q + sum_segments |d|,      beta_0 = 2 A_0 + sum_segments |cz|.
    The functional is F_lam(w) = B(w) + lam * beta_0(w), lam = 3 here.  profile_cost() below is a
    letter-by-letter transcription; the selftest compares it with the compressed search model.

PROOF THAT THE SEARCH IS EXHAUSTIVE (every step is checked by this file or is an elementary lemma)
    Lemma R (reduction).  Deleting an adjacent pair LR, RL or XX from an accepted sorting word gives an
        accepted sorting word with F not larger.  LR / RL: same segment, d and cz change by +1-1 = 0,
        array contents and the final state unchanged, so F is equal.  XX at cursor cell c on the pair
        (x,y): the first X closes segment s1 with value a = cz(s1) (+1 if x is zero 0), the empty middle
        segment has cz = -[y = zero 0] + [y = zero 0] = 0 and d = 0, the second X restores the array and
        starts s3 with cz = -[x = zero 0].  Deleting XX merges s1, s3 into one segment with
        d = d1 + d3 and cz = a + b (b = value of s3), so |d1+d3| <= |d1|+|d3|, |a+b| <= |a|+|b|, while
        q drops by 2 and A_0 by 0 or 2.  Iterating strictly shortens the word, so every accepted sorting
        word reduces to a reduced one (no LR, RL, XX) with F not larger.  Hence
        min over all accepted words = min over reduced accepted words.
    Lemma C (exact segment accounting).  In a reduced word each segment is L^a or R^a, so |d| = a.  A
        segment starts with cz = s in {0, -1} (s = -1 iff the previous X was LZ), changes monotonically
        (L: +1 per crossing, R: -1 per crossing) and is closed by an X that adds e in {0,1} (e = 1 iff
        ZL) or by the end of the word (e = 0).  Case analysis of |s + (+-)c + e|:
            L, s=0: c+e          L, s=-1: 0 crossings -> 1-e, c>=1 -> (c-1)+e
            R, s=0: 0 crossings -> e, c>=1 -> (c-1)+(1-e)        R, s=-1: c+(1-e)
        So |cz| is paid exactly by charging lam per crossing in the contexts listed in step() plus a
        closing charge of lam*e (contexts X0,L0,R0,S) or lam*(1-e) (contexts X1,L1,R1).  The contexts:
            S  start (cz = 0, any letter)         X0 / X1  just after an X, cz = 0 / -1
            L0 L-segment with cz >= 0 (already charged lam*cz)      L1 L-segment with cz = -1
            R0 R-segment with cz = 0          R1 R-segment with cz <= -1 (already charged lam*(|cz|-1))
        Hence F(w) = sum of step() costs along w + final(context).  The remaining cost depends only on
        (vector, context), so min F over reduced words is a shortest path in the finite graph on nodes
        (vector, context) with nonnegative edge costs.  Zeros other than zero 0 carry weight 0 and are
        encoded alike (code Z1): step(), the root test and the zero-zero ban only see zero-ness and
        zero 0.
    Lemma A (abstraction bound).  alpha maps every label to a class code (< 100) and keeps zeros.
        step() reads only zero-ness and the position of zero 0, so step(alpha u, c, x) =
        (alpha t, c', w) whenever step(u, c, x) = (t, c', w), and alpha maps concrete roots to abstract
        roots.  PatternTable.verify() checks on EVERY abstract node and letter that
        h(u,c) <= w + h(t,c') and h(root,c) <= final(c) (consistency; h is not trusted as built).
        Consistency lifts to concrete nodes through alpha, and by induction on path length
        h(node) <= cost of every completion.  h(S) := 0.
    Theorem.  A* from (v, S) with a consistent heuristic is Dijkstra on the nonnegative reduced costs
        w + h(t) - h(u); the first terminal popped has the minimum F over all reduced sorting words.  With
        Lemmas R and C it is the minimum over all accepted sorting words.

    Assumed and not checked here: only that profile_cost() transcribes the group's Lemma 1 bookkeeping
    (the definitions above).  Nothing is read from disk except the certificate JSON.

USAGE
    python3 negcert_check.py negcert-m9-04.json        # the m = 9 {0,4} statement (about 16 s)
    python3 negcert_check.py --selftest                # model checks and small-m exact cross-checks (about 40 s)
"""
import argparse
import heapq
import json
import random
import sys
import time
from array import array
from fractions import Fraction

Z0, Z1 = 100, 101        # zero 0 (weighted) and every other zero; label codes stay below 100
S, X0, X1, L0, L1, R0, R1 = range(7)
CTX = (X0, X1, L0, L1, R0, R1)
CNAME = ('S', 'X0', 'X1', 'L0', 'L1', 'R0', 'R1')
INF = 65535


# ------------------------------------------------------------------ definitions (Profile transcription)
def base_vector(labels, mask):
    """Zero before the first label iff bit 0; after the i-th label iff bit i (lrx_m.base_vector)."""
    v = [0] if mask & 1 else []
    for i, x in enumerate(labels, 1):
        v.append(x)
        if (mask >> i) & 1:
            v.append(0)
    return v


def budget(m, r):
    """T_m(m+r) = m(m+1)/2 + (r-1)(m-2)."""
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def is_root(v):
    m = sum(1 for x in v if x != 0)
    return len(v) > m and list(v[:m]) == list(range(1, m + 1)) and all(x == 0 for x in v[m:])


def profile_cost(vec, word):
    """Lemma 1 bookkeeping, letter by letter, for a unit state (one zero per block, picks = those zeros).
    Returns (B, beta) with beta[j] for the j-th zero from the left of vec, or raises ValueError when the
    word swaps two zeros or does not sort."""
    a = []
    zi = 0
    for x in vec:
        if x == 0:
            a.append(1000 + zi)
            zi += 1
        else:
            a.append(x)
    k, n = zi, len(a)
    c = 0
    q = 0
    d, cz, A = 0, [0] * k, [0] * k
    segs = []
    for ch in word:
        if ch == 'L':
            d += 1
            if a[c] >= 1000:
                cz[a[c] - 1000] += 1
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            if a[c] >= 1000:
                cz[a[c] - 1000] -= 1
        elif ch == 'X':
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x >= 1000 and y >= 1000:
                raise ValueError('word swaps two zeros')
            q += 1
            nxt = [0] * k
            if x >= 1000:                      # ZL swap
                cz[x - 1000] += 1
                A[x - 1000] += 1
            elif y >= 1000:                    # LZ swap
                A[y - 1000] += 1
                nxt[y - 1000] = -1
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


def open_cost(vec, word, lam):
    """B + lam*beta_0 of an arbitrary accepted prefix, closing the last segment at the end (no root test).
    Used only to test the compressed model against the transcription on non-sorting prefixes."""
    a, zi = [], 0
    for x in vec:                              # zero 0 -> 1000, other zeros -> 1001
        if x == 0:
            a.append(1000 if zi == 0 else 1001)
            zi += 1
        else:
            a.append(x)
    n = len(a)
    c = 0
    tot, d, cz = 0, 0, 0
    for ch in word:
        if ch == 'L':
            d += 1
            cz += a[c] == 1000
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            cz -= a[c] == 1000
        else:
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x >= 1000 and y >= 1000:
                return None
            nxt = 0
            if x == 1000:
                cz += 1
                tot += 2 * lam
            elif y == 1000:
                tot += 2 * lam
                nxt = -1
            tot += 1 + abs(d) + lam * abs(cz)
            d, cz = 0, nxt
            a[c], a[c2] = y, x
    return tot + abs(d) + lam * abs(cz)


# ------------------------------------------------------------------ compressed search model (Lemma C)
def encode(vec):
    """Search encoding: zero 0 -> Z0, other zeros -> Z1, labels unchanged."""
    out, zi = [], 0
    for x in vec:
        if x == 0:
            out.append(Z0 if zi == 0 else Z1)
            zi += 1
        else:
            out.append(x)
    return bytes(out)


def step(u, c, ch, lam):
    """One letter from node (u, c) of a reduced word. Returns (t, c', cost) or None if not allowed."""
    if ch == 'L':
        if c == R0 or c == R1:
            return None
        cr = u[0] == Z0
        t = u[1:] + u[:1]
        if c == S or c == X0 or c == L0:
            return t, L0, 1 + lam * cr
        return t, (L0 if cr else L1), 1
    if ch == 'R':
        if c == L0 or c == L1:
            return None
        t = u[-1:] + u[:-1]
        cr = t[0] == Z0
        if c == S or c == X0 or c == R0:
            return t, (R1 if cr else R0), 1
        return t, R1, 1 + lam * cr
    if c == X0 or c == X1 or (u[0] >= 100 and u[1] >= 100):
        return None
    a0 = u[0] == Z0
    a1 = u[1] == Z0
    close = lam * a0 if (c == S or c == L0 or c == R0) else lam * (1 - a0)
    return bytes([u[1], u[0]]) + u[2:], (X1 if a1 else X0), 1 + close + 2 * lam * (a0 or a1)


def final(c, lam):
    return lam if c in (X1, L1, R1) else 0


def roots_of(m, r):
    """Encoded roots: labels 1..m then the r zeros with zero 0 in any of the r places."""
    lab = bytes(range(1, m + 1))
    return {lab + bytes([Z1] * i + [Z0] + [Z1] * (r - 1 - i)) for i in range(r)}


def model_cost(vec, word, lam):
    """F via the compressed model; None if the word is not reduced or is rejected."""
    u, c, tot = encode(vec), S, 0
    for ch in word:
        s = step(u, c, ch, lam)
        if s is None:
            return None
        u, c, w = s
        tot += w
    return tot + final(c, lam), u


# ------------------------------------------------------------------ pattern table (Lemma A)
_INV = {'L': lambda t: t[-1:] + t[:-1], 'R': lambda t: t[1:] + t[:1], 'X': lambda t: bytes([t[1], t[0]]) + t[2:]}
_KIND = {X0: 'X', X1: 'X', L0: 'L', L1: 'L', R0: 'R', R1: 'R'}


class PatternTable:
    """Exact min F-to-go in the abstraction alpha (labels -> class codes); built by backward Dijkstra and
    then verified to be consistent independently of how it was built."""

    def __init__(self, m, r, classes, lam):
        self.lam = lam
        tr = bytearray(range(256))
        for code, labs in enumerate(classes, 1):
            for x in labs:
                tr[x] = code
        if sorted(x for cl in classes for x in cl) != list(range(1, m + 1)):
            raise ValueError('classes must partition 1..m')
        self.tr = bytes(tr)
        self.roots = {g.translate(self.tr) for g in roots_of(m, r)}
        idx, vecs = {}, []
        for g in sorted(self.roots):
            idx[g] = len(vecs)
            vecs.append(g)
        i = 0
        while i < len(vecs):                   # connected component of the abstract roots
            u = vecs[i]
            i += 1
            for t in (u[1:] + u[:1], u[-1:] + u[:-1], bytes([u[1], u[0]]) + u[2:]):
                if t not in idx:
                    idx[t] = len(vecs)
                    vecs.append(t)
        self.idx, self.vecs, self.N = idx, vecs, len(vecs)
        h = array('H', [INF]) * (self.N * 7)
        buckets = {}
        for g in self.roots:
            for c in CTX:
                v = final(c, lam)
                h[idx[g] * 7 + c] = v
                buckets.setdefault(v, []).append(idx[g] * 7 + c)
        val = 0
        while buckets:
            b = buckets.pop(val, None)
            while b:
                node = b.pop()
                if h[node] != val:
                    continue
                j, c2 = divmod(node, 7)
                ch = _KIND[c2]
                u = _INV[ch](vecs[j])
                ju = idx[u] * 7
                for c in CTX:
                    s = step(u, c, ch, lam)
                    if s is not None and s[1] == c2:
                        w = val + s[2]
                        if w < h[ju + c]:
                            h[ju + c] = w
                            buckets.setdefault(w, []).append(ju + c)
            val += 1
        self.h = h

    def verify(self):
        """Consistency on every abstract node and letter; returns (nodes, edges, max h)."""
        h, idx, lam = self.h, self.idx, self.lam
        edges = 0
        hmax = 0
        for j, u in enumerate(self.vecs):
            for c in CTX:
                hv = h[j * 7 + c]
                if hv >= INF:
                    raise AssertionError('unreached abstract node %r %s' % (u, CNAME[c]))
                hmax = max(hmax, hv)
                if u in self.roots and hv > final(c, lam):
                    raise AssertionError('h exceeds final cost at an abstract root')
                for ch in 'LRX':
                    s = step(u, c, ch, lam)
                    if s is None:
                        continue
                    edges += 1
                    if hv > s[2] + h[idx[s[0]] * 7 + s[1]]:
                        raise AssertionError('inconsistent h at %r %s %s' % (u, CNAME[c], ch))
        return self.N * 6, edges, hmax

    def value(self, u, c):
        if c == S:
            return 0
        return self.h[self.idx[u.translate(self.tr)] * 7 + c]


# ------------------------------------------------------------------ exact search (Theorem)
def astar(vec, tables, lam, node_cap=None):
    """Exact min F over reduced accepted sorting words of vec. Returns (F, word, expanded)."""
    v0 = encode(vec)
    m = sum(1 for x in vec if x != 0)
    roots = roots_of(m, len(vec) - m)

    def H(u, c):
        return max([t.value(u, c) for t in tables] or [0])

    best = {(v0, S): 0}
    par = {(v0, S): None}
    heap = [(H(v0, S), 0, v0, S)]
    expanded = 0
    while heap:
        f, g, u, c = heapq.heappop(heap)
        if c == 99:                            # terminal pseudo-node: the word ends here
            key, w = (u, 99), []
            while par[key] is not None:
                key, ch = par[key]
                w.append(ch)
            return g, ''.join(reversed(w)), expanded
        if best[(u, c)] < g:
            continue
        expanded += 1
        if node_cap and expanded > node_cap:
            raise RuntimeError('node cap reached: INCOMPLETE')
        if u in roots:
            tot = g + final(c, lam)
            if best.get((u, 99), 1 << 30) > tot:
                best[(u, 99)] = tot
                par[(u, 99)] = ((u, c), '')
                heapq.heappush(heap, (tot, tot, u, 99))
        for ch in 'LRX':
            s = step(u, c, ch, lam)
            if s is None:
                continue
            t, c2, w = s
            ng = g + w
            if best.get((t, c2), 1 << 30) > ng:
                best[(t, c2)] = ng
                par[(t, c2)] = ((u, c), ch)
                heapq.heappush(heap, (ng + H(t, c2), ng, t, c2))
    return None, None, expanded


def raw_dijkstra(vec, lam):
    """Independent exact oracle for small cases: Dijkstra over (vector, last letter, raw cz) with the
    uncompressed Profile rules (no contexts, no tables). Reduced words only (Lemma R)."""
    v0 = encode(vec)
    m = sum(1 for x in vec if x != 0)
    roots = roots_of(m, len(vec) - m)
    start = (v0, '', 0)
    dist = {start: 0}
    heap = [(0, v0, '', 0)]
    while heap:
        g, u, last, cz = heapq.heappop(heap)
        if last == 'END':
            return g
        if dist[(u, last, cz)] < g:
            continue
        succ = []
        if u in roots:
            succ.append((u, 'END', 0, g + lam * abs(cz)))
        if last != 'R':
            succ.append((u[1:] + u[:1], 'L', cz + (u[0] == Z0), g + 1))
        if last != 'L':
            t = u[-1:] + u[:-1]
            succ.append((t, 'R', cz - (t[0] == Z0), g + 1))
        if last != 'X' and not (u[0] >= 100 and u[1] >= 100):
            e = u[0] == Z0
            inv = e or u[1] == Z0
            succ.append((bytes([u[1], u[0]]) + u[2:], 'X', -1 if u[1] == Z0 else 0,
                         g + 1 + lam * abs(cz + e) + 2 * lam * inv))
        for t, l, z, ng in succ:
            if dist.get((t, l, z), 1 << 30) > ng:
                dist[(t, l, z)] = ng
                heapq.heappush(heap, (ng, t, l, z))
    return None


def reduce_word(w):
    out = []
    for ch in w:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


# ------------------------------------------------------------------ selftest
def selftest(log=print):
    rng = random.Random(20260926)
    ok = True
    # 1. compressed model == transcription (open prefixes, all reduced words up to length 11, 3 states)
    n1 = 0
    for vec in ([0, 9, 8, 7, 6, 0, 5, 4, 3, 2, 1], [0, 5, 4, 0, 3, 2, 1], [3, 0, 1, 0, 2, 0, 4]):
        stack = ['']
        while stack:
            w = stack.pop()
            mc = model_cost(vec, w, 3)
            oc = open_cost(vec, w, 3)
            if (mc is None) != (oc is None) or (mc is not None and mc[0] != oc):
                ok = False
                log('MODEL MISMATCH', vec, w, mc, oc)
            n1 += 1
            if mc is not None and len(w) < 11:
                for ch in 'LRX':
                    if not (w and w[-1] + ch in ('LR', 'RL', 'XX')):
                        stack.append(w + ch)
    log('selftest 1: compressed model = Profile transcription on %d reduced prefixes: %s' % (n1, ok))
    # 2. Lemma R on random words; transcription vs model on random sorting words
    n2 = bad2 = 0
    for m, mask in ((5, 1 | 4), (5, 1 | 8), (6, 1 | 16), (6, 2 | 8 | 32), (4, 1 | 4)):
        vec = base_vector(list(range(m, 0, -1)), mask)
        for _ in range(400):
            pre = ''.join(rng.choice('LRXX') for _ in range(rng.randint(0, 30)))
            w = pre + _bfs_sorter(vec, pre)
            try:
                B, beta = profile_cost(vec, w)
            except ValueError:
                continue
            n2 += 1
            rw = reduce_word(w)
            B2, beta2 = profile_cost(vec, rw)
            mc = model_cost(vec, rw, 3)
            if B2 + 3 * beta2[0] > B + 3 * beta[0] or mc is None or mc[0] != B2 + 3 * beta2[0]:
                bad2 += 1
    ok &= bad2 == 0
    log('selftest 2: %d random sorting words, reduction never increases F, model = transcription: %s'
        % (n2, bad2 == 0))
    # 3. small-m exact: A* with tables = raw Dijkstra (no tables, uncompressed cz)
    cases = [(5, 1 | 4), (5, 1 | 8), (5, 1 | 16), (5, 1 | 2 | 16), (5, 2 | 8), (6, 1 | 4), (6, 1 | 8),
             (6, 1 | 16), (6, 1 | 32), (6, 1 | 8 | 64), (6, 4 | 32)]
    n3 = bad3 = 0
    for m, mask in cases:
        vec = base_vector(list(range(m, 0, -1)), mask)
        r = len(vec) - m
        for lam in (1, 3):
            classes = [list(range(m, m // 2, -1)), list(range(m // 2, 0, -1))]
            tab = PatternTable(m, r, classes, lam)
            tab.verify()
            F, w, _ = astar(vec, [tab], lam)
            G = raw_dijkstra(vec, lam)
            B, beta = profile_cost(vec, w)
            n3 += 1
            good = F == G == B + lam * beta[0]
            bad3 += not good
            log('  m=%d mask=%s lam=%d: A* %s, raw Dijkstra %s, witness B=%d beta=%s %s'
                % (m, bin(mask), lam, F, G, B, beta, 'ok' if good else 'MISMATCH'))
    ok &= bad3 == 0
    log('selftest 3: %d small exact cases agree: %s' % (n3, bad3 == 0))
    return ok


def _bfs_sorter(vec, pre):
    """Shortest completion of an accepted prefix to a sorting word (plain BFS on the vector graph)."""
    from collections import deque
    u = encode(vec)
    for ch in pre:
        if ch == 'L':
            u = u[1:] + u[:1]
        elif ch == 'R':
            u = u[-1:] + u[:-1]
        else:
            if u[0] >= 100 and u[1] >= 100:
                return ''
            u = bytes([u[1], u[0]]) + u[2:]
    m = sum(1 for x in vec if x != 0)
    roots = roots_of(m, len(vec) - m)
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


# ------------------------------------------------------------------ certificate
def check_certificate(path, log=print):
    cert = json.load(open(path))
    t0 = time.time()
    m, labels, mask, lam = cert['m'], cert['labels'], cert['mask'], cert['lam']
    vec = base_vector(labels, mask)
    r = len(vec) - m
    problems = []
    if vec != cert['base']:
        problems.append('base vector %s != certificate %s' % (vec, cert['base']))
    T, s = budget(m, r), m - 2
    if [T, s] != [cert['T'], cert['s']]:
        problems.append('T, s mismatch')
    log('statement: m=%d base=%s  min over accepted sorting words of B + %d*beta_0 >= %d'
        % (m, vec, lam, cert['claim_min']))
    tables = []
    for classes in cert['abstractions']:
        t1 = time.time()
        tab = PatternTable(m, r, classes, lam)
        nodes, edges, hmax = tab.verify()
        hs = min(w + tab.value(t, c) for ch in 'LRX' for s_ in [step(encode(vec), S, ch, lam)] if s_
                 for t, c, w in [s_])
        log('pattern table %s: %d abstract vectors, %d nodes, %d edges, consistent; max h %d; '
            'bound at start %d (%.1f s)' % (classes, tab.N, nodes, edges, hmax, hs, time.time() - t1))
        tables.append(tab)
    t1 = time.time()
    F, word, expanded = astar(vec, tables, lam)
    log('A*: exact minimum %s after %d expansions (%.1f s); optimal word %s' % (F, expanded, time.time() - t1, word))
    if F != cert['claim_min']:
        problems.append('exact minimum %s != claimed %s' % (F, cert['claim_min']))
    B, beta = profile_cost(vec, word)
    log('  re-priced by the transcription: len %d, B=%d, beta=%s, F=%d' % (len(word), B, beta, B + lam * beta[0]))
    if B + lam * beta[0] != F:
        problems.append('A* word re-prices to a different value')
    for wit in cert['witnesses']:
        B, beta = profile_cost(vec, wit['word'])
        good = [B, beta] == [wit['B'], wit['beta']] and B + lam * beta[0] == cert['claim_min']
        log('witness %s: B=%d beta=%s F=%d %s' % (wit['word'], B, beta, B + lam * beta[0], 'ok' if good else 'BAD'))
        if not good:
            problems.append('witness mismatch')
    # mixture consequence (criterion (7) / (8) at the unit origin, box unbounded)
    need = Fraction(T + 1) + lam * s
    log('root mixture needs Bbar < T+1 = %d and betabar_0 <= s = %d, so Bbar + %d betabar_0 < %s; '
        'every word, hence every mixture, has >= %s: %s'
        % (T + 1, s, lam, need, F, 'NO ROOT-LEAF CERTIFICATE' if F is not None and F >= need else 'not refuted'))
    if not (F is not None and F >= need):
        problems.append('bound does not refute the root leaf')
    log('total %.1f s' % (time.time() - t0))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cert', nargs='?')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    ok = True
    if a.selftest:
        ok &= selftest()
    if a.cert:
        probs = check_certificate(a.cert)
        for p in probs:
            print('PROBLEM:', p)
        ok &= not probs
    if not a.selftest and not a.cert:
        ap.error('give a certificate or --selftest')
    print('VERIFIED' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
