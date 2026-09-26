"""Mechanical check of every intermediate claim of WORDR1-PROOF.md (Lemmas P, A, B, C, D, E and the theorem).

The proof predicts, from closed formulas in m only, the carry count s of every growth step of word_R1(m), the
exact block decomposition of the word into walks and sweeps, the cell contents and cursor after every step of
both cores, the zeros passed by every walk, the stopping step of core 2, the Lemma 1 segment terms (d, cz) of
every segment, and the totals. This script builds those predictions WITHOUT calling core_word, then executes the
actual word_R1(m) (imported from reversal_orbit.py) letter by letter with its own zero-identity executor and
compares, block by block. At every step boundary it also evaluates core_word's carry rule (the rank comparison
loop) and its stopping test srt() on the executed cells. It also compares against lrx_m.Profile.

Stdlib only; no provider calls; writes nothing.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordr1_proof_check.py          # m = 9..60
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordr1_proof_check.py 9 200
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrations import lrx_m as C  # noqa: E402
from reversal_orbit import word_R1  # noqa: E402

Z0, Z1 = 'Z0', 'Z1'  # Z0 starts in cell 1 (gap 1, Profile block 0), Z1 in cell n-1 (gap m, block 1)


# ------------------------------------------------------------------ parameters of the proof (section 1)
def params(m):
    u, rho = m // 4, m % 4
    n = m + 2
    t = (m - 3) // 4
    k1 = m // 2
    K = k1 - (1 if rho == 2 else 0)            # last full-carry step of core 1
    p, q = (K + 1) // 2, K // 2                 # l-steps and r-steps among steps 1..K
    N2 = n - 1 - p - q                          # |R2| = m + 1 - K
    s2 = k1 + 1
    d2 = 'r' if rho == 1 else 'l'
    return dict(u=u, rho=rho, n=n, t=t, k1=k1, K=K, p=p, q=q, N2=N2, s2=s2, d2=d2)


def initial(m):
    return [m, Z0] + list(range(m - 1, 0, -1)) + [Z1]


def rank(m, t, x):
    """core_word's rank: labels t+1..m, then the (tied) zeros, then 1..t."""
    if x in (Z0, Z1):
        return m - t
    return x - t - 1 if x > t else m - t + x


# ------------------------------------------------------------------ predictions (formulas of the proof only)
def core1_state(m, k):
    """Lemma A: cells, cursor, lo, hi after k steps of core 1 (k = 1..K), plus the rho = 2 no-op step."""
    P = params(m)
    n = P['n']
    if k == 1:
        cells = initial(m)
        cells[n - 1], cells[0] = m, Z1
        return cells, n - 1, n - 1, 0
    pk, qk = (k + 1) // 2, k // 2
    lo, hi = (n - pk) % n, qk
    cells = {j: m + 1 - j for j in range(qk + 1, n - pk)}               # untouched cells q_k+1 .. n-1-p_k
    arc = list(range(m - qk + 1, m + 1)) + [Z1, Z0] + list(range(1, pk))
    for i, x in enumerate(arc):
        cells[(lo + i) % n] = x
    assert len(cells) == n
    cur = lo if k % 2 == 0 else qk - 1
    return [cells[j] for j in range(n)], cur, lo, hi


def core2_sides(m):
    P = params(m)
    other = 'l' if P['d2'] == 'r' else 'r'
    return [P['d2'] if i % 2 == 1 else other for i in range(1, P['N2'])]


def core2_state(m, i):
    """Lemma B: cells, cursor, lo', hi' after i steps of core 2 (i = 0..N2-1)."""
    P = params(m)
    cells, _, _, _ = core1_state(m, P['K'])
    sides = core2_sides(m)[:i]
    lo, hi = P['s2'] - sides.count('l'), P['s2'] + sides.count('r')
    for j in range(lo, hi + 1):
        cells[j] = m + 1 - (lo + hi - j)
    cur = None if i == 0 else (lo if sides[-1] == 'r' else hi - 1)
    return cells, cur, lo, hi


def w0_prediction(m):
    """Lemma C: (start cursor, target, direction, length)."""
    P = params(m)
    u, rho, n = P['u'], P['rho'], P['n']
    c1 = n - u if rho != 3 else u - 1
    t0 = P['s2'] if P['d2'] == 'r' else P['s2'] - 1
    d, ln = {0: ('R', u + 2), 1: ('R', u + 2), 2: ('R', u + 3), 3: ('L', u + 2)}[rho]
    return c1, t0, d, ln


def predicted_s(m):
    """Lemma P: the carry count s of every growth step, in order (core 1 then core 2)."""
    P = params(m)
    s = [1, 0] + list(range(3, P['K'] + 1)) + ([0] if P['rho'] == 2 else [])
    return s + list(range(1, P['N2']))


def predicted_blocks(m):
    P = params(m)
    blocks = [('c1walk1', 'R'), ('c1sweep1', 'X'), ('c1step2', '')]
    for k in range(3, P['K'] + 1):
        blocks.append(('c1walk%d' % k, 'R' if k % 2 else 'L'))
        blocks.append(('c1sweep%d' % k, 'X' + ('LX' if k % 2 else 'RX') * (k - 1)))
    if P['rho'] == 2:
        blocks.append(('c1step%d' % (P['K'] + 1), ''))
    _, _, d, ln = w0_prediction(m)
    blocks.append(('W0', d * ln))
    sides = core2_sides(m)
    for i, sd in enumerate(sides, 1):
        if i >= 2:
            blocks.append(('c2walk%d' % i, 'R' if sides[i - 2] == 'r' else 'L'))
        blocks.append(('c2sweep%d' % i, 'X' + ('RX' if sd == 'r' else 'LX') * (i - 1)))
    blocks.append(('Wf', 'R' * (P['p'] - 1)))
    return blocks


# ------------------------------------------------------------------ own executor with zero identities
class Exec:
    def __init__(self, m):
        self.n = m + 2
        self.cell = initial(m)
        self.c = 0
        self.segs = [[0, {Z0: 0, Z1: 0}]]      # Lemma 1 terms as lrx_m.Profile defines them
        self.passes = []                        # zeros left by L / arrived on by R
        self.A = {Z0: 0, Z1: 0}

    def step(self, ch):
        n, cell = self.n, self.cell
        seg = self.segs[-1]
        if ch == 'L':
            x = cell[self.c]
            seg[0] += 1
            if x in (Z0, Z1):
                seg[1][x] += 1
                self.passes.append(x)
            self.c = (self.c + 1) % n
        elif ch == 'R':
            self.c = (self.c - 1) % n
            x = cell[self.c]
            seg[0] -= 1
            if x in (Z0, Z1):
                seg[1][x] -= 1
                self.passes.append(x)
        else:
            j = (self.c + 1) % n
            x, y = cell[self.c], cell[j]
            if x in (Z0, Z1) and y in (Z0, Z1):
                raise AssertionError('zero-zero swap')
            nxt = {Z0: 0, Z1: 0}
            if x in (Z0, Z1):
                seg[1][x] += 1
                self.A[x] += 1
            elif y in (Z0, Z1):
                nxt[y] = -1
                self.A[y] += 1
            cell[self.c], cell[j] = y, x
            self.segs.append([0, nxt])


def carry_count(m, t, cell, lo, hi, side):
    """core_word's comparison loop, evaluated on the given cells (the object of Lemma P)."""
    n = len(cell)
    ln = (hi - lo) % n + 1
    s = 0
    if side == 'r':
        e = cell[(hi + 1) % n]
        while s < ln and rank(m, t, cell[(hi - s) % n]) > rank(m, t, e):
            s += 1
    else:
        e = cell[(lo - 1) % n]
        while s < ln and rank(m, t, cell[(lo + s) % n]) < rank(m, t, e):
            s += 1
    return s


def srt(m, cell):
    n = len(cell)
    i = cell.index(1)
    return [cell[(i + x) % n] for x in range(m)] == list(range(1, m + 1))


def check(m, bad):
    def req(cond, what):
        if not cond:
            bad.append((m, what))

    P = params(m)
    n, t, K, p, q, N2, rho, u = P['n'], P['t'], P['K'], P['p'], P['q'], P['N2'], P['rho'], P['u']
    w = word_R1(m)
    blocks = predicted_blocks(m)
    req(''.join(b for _, b in blocks) == w, 'word != predicted block decomposition')
    if ''.join(b for _, b in blocks) != w:
        return
    # parameter identities of section 1
    req(t == (u - 1 if rho != 3 else u), 't = u-1 (rho != 3), u (rho = 3)')
    req((K, p, q) == {0: (2 * u, u, u), 1: (2 * u, u, u), 2: (2 * u, u, u), 3: (2 * u + 1, u + 1, u)}[rho],
        '(K, p, q) table')
    req(N2 == m + 1 - K, 'N2 = m+1-K')
    sides = core2_sides(m)
    req(sides.count('l') == P['s2'] - (q + 1) and sides.count('r') == n - 1 - p - P['s2'], 'Lemma B side counts')
    req(sides[-1] == 'r', 'Lemma B last core-2 step is r')
    # labels of R2 are all > t (full carries in core 2)
    req(all(m + 1 - j > t for j in range(q + 1, n - p)), 'R2 labels > t')
    ex = Exec(m)
    s_pred = predicted_s(m)
    s_seen = []
    # step boundaries: evaluate the carry rule on the executed cells before each growth step
    c1_sides = ['l' if k % 2 else 'r' for k in range(1, P['k1'] + 1)]
    lo = hi = 0

    def pre_step(side, lo_, hi_):
        s_seen.append(carry_count(m, t, ex.cell, lo_, hi_, side))

    for tag, letters in blocks:
        # before the first letter of a growth step: record the carry count of that step
        if tag.startswith('c1walk') or tag.startswith('c1step'):      # first block of core-1 step k
            k = int(tag[6:])
            side = c1_sides[k - 1]
            pre_step(side, lo, hi)
            if side == 'r':
                hi = (hi + 1) % n
            else:
                lo = (lo - 1) % n
        elif tag == 'W0':
            req(ex.c == w0_prediction(m)[0], 'Lemma C W0 start cursor')
            c2lo = c2hi = P['s2']
            c2i = 0
            req(not srt(m, ex.cell), 'srt() false before core 2')
        elif tag.startswith('c2sweep'):
            i = int(tag[7:])
            if i == 1:
                pre_step(sides[0], c2lo, c2hi)
        elif tag.startswith('c2walk'):
            i = int(tag[6:])
            req(not srt(m, ex.cell), 'srt() false before core-2 step %d' % i)
            pre_step(sides[i - 1], c2lo, c2hi)
        npass = len(ex.passes)
        for ch in letters:
            ex.step(ch)
        if tag == 'c1sweep1' or tag.startswith('c1sweep') or tag == 'c1step2':
            k = 1 if tag == 'c1sweep1' else (2 if tag == 'c1step2' else int(tag[7:]))
            cells, cur, plo, phi = core1_state(m, k)
            req(ex.cell == cells, 'Lemma A cells after core-1 step %d' % k)
            req(ex.c == cur, 'Lemma A cursor after core-1 step %d' % k)
            req((lo, hi) == (plo, phi), 'Lemma A lo, hi after core-1 step %d' % k)
        elif tag.startswith('c1step'):          # rho = 2 no-op step K+1
            cells, cur, _, _ = core1_state(m, K)
            req(ex.cell == cells and ex.c == cur, 'Lemma A: the no-op step changes nothing')
            req(lo == (n - p - 1) % n and ex.cell[lo] == u, 'Lemma A: no-op step leaves label u on cell n-1-u')
        elif tag.startswith('c1walk'):
            want = [Z1] if tag == 'c1walk1' else ([Z0] if tag == 'c1walk4' else [])
            req(ex.passes[npass:] == want, 'Lemma E walk zero passes %s (%s)' % (ex.passes[npass:], tag))
        elif tag == 'W0':
            c1, t0, d, ln = w0_prediction(m)
            req(ex.c == t0, 'Lemma C W0 end cursor')
            req(ex.passes[npass:] == [], 'Lemma C W0 passes a zero')
            fwd = (t0 - c1) % n
            req((d == 'L') == (fwd <= n - fwd) and ln == (fwd if d == 'L' else n - fwd), 'Lemma C goto direction')
        elif tag.startswith('c2sweep'):
            i = int(tag[7:])
            if sides[i - 1] == 'r':
                c2hi += 1
            else:
                c2lo -= 1
            cells, cur, plo, phi = core2_state(m, i)
            req(ex.cell == cells, 'Lemma B cells after core-2 step %d' % i)
            req(ex.c == cur, 'Lemma B cursor after core-2 step %d' % i)
            req((c2lo, c2hi) == (plo, phi), 'Lemma B lo, hi after core-2 step %d' % i)
        elif tag.startswith('c2walk'):
            req(ex.passes[npass:] == [], 'Lemma B core-2 walk passes a zero')
        elif tag == 'Wf':
            req(ex.passes[npass:] == [], 'Lemma C Wf passes a zero')
            req(ex.c == (q - p + 2) % n and ex.cell[ex.c] == 1, 'Lemma C Wf ends on label 1 at cell q-p+2')
    req(s_seen == s_pred, 'Lemma P carry counts %s != %s' % (s_seen, s_pred))
    req(srt(m, ex.cell), 'srt() true after core 2')
    req((c2lo, c2hi) == (q + 1, n - 1 - p), 'Lemma B final arc = R2')
    fin = ex.cell[ex.c:] + ex.cell[:ex.c]
    req(fin == list(range(1, m + 1)) + [Z1, Z0], 'final state (1..m, Z1, Z0)')
    st = C.base_vector(list(range(m, 0, -1)), 2 | 1 << m)
    req(st == [m, 0] + list(range(m - 1, 0, -1)) + [0], 'unit base = (m,0,m-1,..,1,0)')
    req(C.is_root(C.run_naive(st, w)) and C.is_root(C.run(st, w)), 'run_naive and run sort')
    # Lemma D
    c1 = sum(len(b) for tg, b in blocks if tg.startswith('c1'))
    c2 = sum(len(b) for tg, b in blocks if tg.startswith('c2'))
    ln0 = w0_prediction(m)[3]
    req(c1 == K * (K + 1) - 4, 'Lemma D core 1 = K(K+1)-4')
    req(c2 == (N2 - 1) ** 2 + N2 - 2, 'Lemma D core 2 = (N2-1)^2+N2-2')
    req(len(w) == K * (K + 1) - 4 + (N2 - 1) ** 2 + N2 - 2 + ln0 + p - 1, 'Lemma D total')
    T = C.budget(m, 2)
    req(len(w) - T == (0 if rho == 2 else -2), 'Theorem length - T')
    nX = w.count('X')
    req(nX == 1 + K * (K + 1) // 2 - 3 + N2 * (N2 - 1) // 2, 'Lemma D #X')
    # Lemma E
    req(len(ex.segs) == nX + 1, 'Lemma E segment count')
    for g, (d, cz) in enumerate(ex.segs):
        req(cz == {Z0: 0, Z1: 0}, 'Lemma E cz of segment %d: %s' % (g, cz))
    letters_between = w.split('X')
    req(all(set(s) <= {'L'} or set(s) <= {'R'} for s in letters_between), 'Lemma E unidirectional segments')
    req([len(s) for s in letters_between] == [abs(d) for d, _ in ex.segs], 'Lemma E |d| = letter count')
    req(ex.A == {Z0: K - 2, Z1: K - 1}, 'Lemma E A = (K-2, K-1): %s' % ex.A)
    beta = [2 * (K - 2), 2 * (K - 1)]
    want_beta = {0: [m - 4, m - 2], 1: [m - 5, m - 3], 2: [m - 6, m - 4], 3: [m - 5, m - 3]}[rho]
    req(beta == want_beta, 'Theorem beta by m mod 4')
    pr = C.Profile(st, w)
    req(pr.A == [K - 2, K - 1], 'Profile A')
    req(pr.base == len(w), 'Profile B = length')
    req(pr.beta == beta, 'Profile beta')
    req(pr.same_sign, 'Profile same_sign')
    req([(d, list(cz)) for d, cz in pr.segs] == [(d, [cz[Z0], cz[Z1]]) for d, cz in ex.segs],
        'Profile segments = own segments')
    # corollary: criterion (7) numbers with weight 1
    ok7, Bb, bb = C.mixture_criterion([(pr.base, pr.beta)], [1], 2, m=m)
    req(ok7 and pr.base <= T and max(pr.beta) <= m - 2, 'Corollary: B <= T, beta <= m-2, mixture_criterion')


def main():
    lo_m = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    hi_m = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    bad = []
    for m in range(lo_m, hi_m + 1):
        check(m, bad)
    print('m = %d..%d: %d values of m' % (lo_m, hi_m, hi_m - lo_m + 1))
    print('mismatches (Lemmas P, A-E, theorem, corollary): %d' % len(bad))
    for b in bad[:20]:
        print('  ', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
