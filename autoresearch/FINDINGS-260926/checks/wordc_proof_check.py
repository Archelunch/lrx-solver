"""Mechanical check of every intermediate claim of WORDC-PROOF.md (Lemmas A-E and the theorem).

The proof predicts, from closed formulas in (m, a) only, the exact block decomposition of word_C(m, a) into
walks and sweeps, the cell contents and cursor after every block, the cells passed by W0 and Wf, the Lemma 1
segment terms (d, cz) of every segment, and the totals.  This script builds those predictions WITHOUT calling
word_C's grow/goto, then executes the actual word_C(m, a) (imported from reversal_m13.py) letter by letter with
its own zero-identity executor and compares, block by block.  It also compares against lrx_m.Profile.

Stdlib only; no provider calls; writes nothing.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/wordc_proof_check.py
"""
import sys
from fractions import Fraction as Fr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrations import lrx_m as C  # noqa: E402
from reversal_m13 import word_C  # noqa: E402

Z0, Z1 = 'Z0', 'Z1'  # zero atoms: Z0 starts in cell 0 (Profile block 0), Z1 in cell n-1 (block 1)


# ------------------------------------------------------------------ predictions (formulas of the proof only)
def core1_state(m, k):
    """Lemma A: cell map and cursor after k sweeps of core 1 (k = 0..a)."""
    n = m + 2
    qk, pk = (k + 1) // 2, k // 2
    lo = (n - 1 - pk) % n
    cells = {j: m + 1 - j for j in range(qk + 1, n - 1 - pk)}          # untouched cells q_k+1 .. n-2-p_k
    arc = list(range(m - qk + 1, m + 1)) + [Z1, Z0] + list(range(1, pk + 1))
    for i, x in enumerate(arc):
        cells[(lo + i) % n] = x
    assert len(cells) == n
    cur = 0 if k == 0 else (lo if k % 2 else (qk - 1) % n)
    return [cells[j] for j in range(n)], cur, lo, qk


def core2_plan(m, a):
    r = m - a
    n = m + 2
    q, p = (a + 1) // 2, a // 2
    first = 'r' if r % 2 == 0 else 'l'
    right = r // 2 if r % 2 == 0 else (r - 1) // 2
    start = n - 2 - p - right
    sides = [first if i % 2 == 1 else ('l' if first == 'r' else 'r') for i in range(1, r)]
    return r, n, q, p, first, right, start, sides


def core2_state(m, a, i):
    """Lemma B: cell map, cursor, arc after i sweeps of core 2 (i = 1..r-1)."""
    r, n, q, p, first, right, start, sides = core2_plan(m, a)
    cells, _, _, _ = core1_state(m, a)
    nr = sides[:i].count('r')
    nl = i - nr
    lo, hi = start - nl, start + nr
    for j in range(lo, hi + 1):
        cells[j] = m + 1 - (lo + hi - j)
    cur = lo if sides[i - 1] == 'r' else hi - 1
    return cells, cur, lo, hi


def w0_prediction(m, a):
    """Lemma C: start cursor c0, target t, direction, length, zero passes of W0."""
    r, n, q, p, first, right, start, sides = core2_plan(m, a)
    c0 = n - 1 - p if a % 2 else p - 1
    t = start if first == 'r' else start - 1
    if a % 2 and r % 2 == 0:
        d, ln = 'R', r // 2 + 1
    elif a % 2 and a >= 3:
        d, ln = 'R', (r + 3) // 2
    elif a == 1:                                  # a = 1, r odd, i.e. m even: tie, goto goes L
        d, ln = 'L', (r + 3) // 2
    elif r % 2 == 0:
        d, ln = 'L', r // 2 + 1
    else:
        d, ln = 'L', (r + 1) // 2
    tie = a == 1 and r % 2 == 1
    return c0, t, d, ln, tie


def predicted_blocks(m, a):
    """The word as (tag, letters) blocks, from the proof's formulas only."""
    blocks = []
    for k in range(1, a + 1):
        if k >= 2:
            blocks.append(('c1walk%d' % k, 'R' if k % 2 == 0 else 'L'))
        blocks.append(('c1sweep%d' % k, 'X' + ('RX' if k % 2 else 'LX') * k))
    r, n, q, p, first, right, start, sides = core2_plan(m, a)
    _, _, d, ln, _ = w0_prediction(m, a)
    blocks.append(('W0', d * ln))
    for i, s in enumerate(sides, 1):
        if i >= 2:
            blocks.append(('c2walk%d' % i, 'R' if sides[i - 2] == 'r' else 'L'))
        blocks.append(('c2sweep%d' % i, 'X' + ('RX' if s == 'r' else 'LX') * (i - 1)))
    blocks.append(('Wf', 'R' * p))
    return blocks


# ------------------------------------------------------------------ own executor with zero identities
class Exec:
    def __init__(self, m):
        self.n = m + 2
        self.cell = [Z0] + list(range(m, 0, -1)) + [Z1]
        self.c = 0
        self.segs = [[0, {Z0: 0, Z1: 0}]]      # Lemma 1 terms as lrx_m.Profile defines them
        self.passes = []                        # zeros left by L / arrived on by R, per letter

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
            elif y in (Z0, Z1):
                nxt[y] = -1
            cell[self.c], cell[j] = y, x
            self.segs.append([0, nxt])


def check(m, a, bad):
    def req(cond, what):
        if not cond:
            bad.append((m, a, what))

    n, r, q, p = m + 2, m - a, (a + 1) // 2, a // 2
    w = word_C(m, a)
    blocks = predicted_blocks(m, a)
    req(''.join(b for _, b in blocks) == w, 'word != predicted block decomposition')
    if ''.join(b for _, b in blocks) != w:
        return
    ex = Exec(m)
    # Lemma A at k = 0
    cells, cur, _, _ = core1_state(m, 0)
    req(ex.cell == cells and ex.c == cur, 'A k=0')
    ex_segs_before_w0 = None
    for tag, letters in blocks:
        npass = len(ex.passes)
        nseg = len(ex.segs)
        for ch in letters:
            ex.step(ch)
        if tag.startswith('c1sweep'):
            k = int(tag[7:])
            cells, cur, lo, hi = core1_state(m, k)
            req(ex.cell == cells, 'Lemma A cells after core-1 sweep %d' % k)
            req(ex.c == cur, 'Lemma A cursor after core-1 sweep %d' % k)
        elif tag.startswith('c1walk') or tag.startswith('c2walk'):
            # Lemma E: only the L walk after core-1 sweep 2 passes a zero (it leaves Z0 in cell 0)
            want = [Z0] if tag == 'c1walk3' else []
            req(ex.passes[npass:] == want, 'inter-sweep walk zero passes %s (%s)' % (ex.passes[npass:], tag))
        elif tag == 'W0':
            c0, t, d, ln, tie = w0_prediction(m, a)
            req(ex.c == t, 'Lemma C W0 end cursor')
            got = ex.passes[npass:]
            # Lemma C: W0 leaves Z1 (cell 0) then Z0 (cell 1) in the tie; leaves Z0 (cell 0) first if a = 2
            want = [Z1, Z0] if tie else ([Z0] if a == 2 else [])
            req(got == want, 'Lemma C W0 zero passes %s' % got)
            req(got[:1] == [] or letters[0] == 'L', 'Lemma C: a zero passed by W0 is left by its first letters')
            ex_segs_before_w0 = nseg
        elif tag.startswith('c2sweep'):
            i = int(tag[7:])
            cells, cur, lo, hi = core2_state(m, a, i)
            req(ex.cell == cells, 'Lemma B cells after core-2 sweep %d' % i)
            req(ex.c == cur, 'Lemma B cursor after core-2 sweep %d' % i)
        elif tag == 'Wf':
            req(len(ex.passes) == npass, 'Lemma C Wf passes a zero')
            req(ex.c == q - p + 1 and ex.cell[ex.c] == 1, 'Lemma C Wf ends on label 1 at cell q-p+1')
    # Lemma C: cursor before W0 (checked via the end of core 1), core-2 region, start/right bookkeeping
    r_, n_, q_, p_, first, right, start, sides = core2_plan(m, a)
    req(sides[-1] == 'r', 'Lemma B last core-2 sweep is r')
    req(start - sides.count('l') == q + 1 and start + sides.count('r') == n - 2 - p, 'Lemma B final arc')
    req(right == (r - 1 + (first == 'r')) // 2 and start == n - 2 - p - (r - 1 + (first == 'r')) // 2,
        'Lemma B right/start = code formulas')
    # final state
    fin = ex.cell[ex.c:] + ex.cell[:ex.c]
    req(fin == list(range(1, m + 1)) + [Z1, Z0], 'final state is (1..m, Z1, Z0)')
    req(C.is_root(C.run_naive([0] + list(range(m, 0, -1)) + [0], w)), 'run_naive sorts')
    # Lemma D
    c1 = sum(len(b) for t, b in blocks if t.startswith('c1'))
    c2 = sum(len(b) for t, b in blocks if t.startswith('c2'))
    _, _, _, ln0, tie = w0_prediction(m, a)
    req(c1 == a * a + 3 * a - 1, 'Lemma D core 1 = a^2+3a-1')
    req(c2 == (r - 1) ** 2 + r - 2, 'Lemma D core 2 = (r-1)^2+r-2')
    req(ln0 == (r // 2 + 1 if r % 2 == 0 else ((r + 3) // 2 if a % 2 else (r + 1) // 2)), 'Lemma C W0 length')
    req(len(w) == a * a + 3 * a - 1 + (r - 1) ** 2 + r - 2 + ln0 + p, 'Lemma D total')
    T = C.budget(m, 2)
    req(Fr(len(w) - T) == 2 * (Fr(a) - Fr(m - 2, 2)) ** 2 - 1 - Fr(m % 2, 2), 'Theorem length formula')
    nX = w.count('X')
    req(nX == a * (a + 3) // 2 + r * (r - 1) // 2, 'Lemma D #X')
    # Lemma E: segment terms
    req(len(ex.segs) == nX + 1, 'Lemma E segment count')
    for g, (d, cz) in enumerate(ex.segs):
        want = {Z0: 0, Z1: 0}
        if g == 0:
            want = {Z0: 1, Z1: 0}
        elif tie and g == ex_segs_before_w0 - 1:
            want = {Z0: 1, Z1: 1}
        req(cz == want, 'Lemma E cz of segment %d: %s' % (g, cz))
        # unidirectional: the segment's letters are one repeated letter, so |d| = its letter count
    letters_between = w.split('X')
    req(all(set(s) <= {'L'} or set(s) <= {'R'} for s in letters_between), 'Lemma E unidirectional segments')
    req([len(s) for s in letters_between] == [abs(d) for d, _ in ex.segs], 'Lemma E |d| = letter count')
    A0 = A1 = a
    beta = [4, 3] if tie else [2 * a + 1, 2 * a]
    req(beta == [2 * A0 + sum(abs(cz[Z0]) for _, cz in ex.segs), 2 * A1 + sum(abs(cz[Z1]) for _, cz in ex.segs)],
        'Lemma E beta from own segments')
    # cross-check with the repository's Profile
    pr = C.Profile([0] + list(range(m, 0, -1)) + [0], w)
    req(pr.A == [a, a], 'Profile A = (a, a)')
    req(pr.base == len(w), 'Profile B = length')
    req(pr.beta == beta, 'Profile beta')
    req(pr.same_sign, 'Profile same_sign')
    req([(d, list(cz)) for d, cz in pr.segs] == [(d, [cz[Z0], cz[Z1]]) for d, cz in ex.segs],
        'Profile segments = own segments')


def main():
    lo_m = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    hi_m = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    bad, pairs = [], 0
    for m in range(lo_m, hi_m + 1):
        for a in range(1, m - 1):
            check(m, a, bad)
            pairs += 1
    cor = []
    for m in range(max(lo_m, 9), hi_m + 1):
        T = C.budget(m, 2)
        if m % 2:
            pr = C.Profile([0] + list(range(m, 0, -1)) + [0], word_C(m, (m - 3) // 2))
            ok = pr.base == T - 1 and pr.beta == [m - 2, m - 3]
        else:
            p1 = C.Profile([0] + list(range(m, 0, -1)) + [0], word_C(m, (m - 2) // 2))
            p2 = C.Profile([0] + list(range(m, 0, -1)) + [0], word_C(m, (m - 4) // 2))
            ok = ((p1.base, p1.beta) == (T - 1, [m - 1, m - 2]) and (p2.base, p2.beta) == (T + 1, [m - 3, m - 4])
                  and Fr(p1.base + p2.base, 2) == T and [Fr(x + y, 2) for x, y in zip(p1.beta, p2.beta)]
                  == [m - 2, m - 3])
        if not ok:
            cor.append(m)
    print('m = %d..%d, pairs (m, a) with 1 <= a <= m-2: %d' % (lo_m, hi_m, pairs))
    print('mismatches (Lemmas A-E, theorem): %d' % len(bad))
    for b in bad[:20]:
        print('  ', b)
    print('corollary failures: %d %s' % (len(cor), cor))
    sys.exit(1 if bad or cor else 0)


if __name__ == '__main__':
    main()
