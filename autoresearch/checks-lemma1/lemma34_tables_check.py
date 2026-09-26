"""Exact-table sanity checks of Lemma 3 (comparison transfer), formula (11) and
Lemma 4 (projection) at m = 9, 10.

Read-only.  Uses the complete one-byte BFS tables (via lemma1_tables_check.Tables)
and integrations/lrx_m.py.  Ranks, prefix counts, the comparator run and the
projection are re-implemented here from the manuscript text, independently of
lrx_m, and the two are compared.

Part T  transfer.  Reference Q = (refined) unit base of a random family, W a
        random-tie shortest word (or one letter + shortest word), a cut not
        crossed by W with #X(W) = inv(Q).  P has Q's zero positions and P <= Q
        in the prefix order (9) (Bruhat moves on Q's window ranks, or random
        label orders filtered by (9)).  At z = 0 every comparison step is
        checked against (9) and (10).  For every z within table range the
        lifted word lift_z(W) is compare-run on E_z(P), and it is checked that
        E_z(P) <= E_z(Q), the run sorts E_z(P) with inv(E_z P) swaps, its
        length is <= (11) (= when W is same-signed), and d(E_z P) <= length.
        Category 'proj+trans' uses a projected (non-geodesic) reference.
Part P  projection.  Parent = (refined) unit base with a sorting word; delete a
        random nonempty proper set of zero atoms.  The per-letter invariant of
        Lemma 4 is checked, the projected word sorts the child, and for every z
        within table range proj(lift_z W) = lift_z(proj W) letter for letter,
        both sort E_z(child), and d(E_z child) <= F_child(z).
Part R  section 7: beta_j = 3A_j + B_j - 2F_j and the resource increment
        table, every zero its own atom, on freely reduced shortest words.
Negative control: P not <= Q; counts how often the comparison run fails.

Usage:  python autoresearch/checks-lemma1/lemma34_tables_check.py [--seed 260926]
"""
import argparse
import collections
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from integrations import lrx_m as C  # noqa: E402
from lemma1_tables_check import Tables, geodesic, random_family, step, z_vectors  # noqa: E402

RMAX = {9: 6, 10: 3}
RMIN = {9: 1, 10: 2}


# ------------------------------------------------ independent primitives
def execute(v, w):
    v = list(v)
    for ch in w:
        if ch == 'L':
            v = v[1:] + v[:1]
        elif ch == 'R':
            v = v[-1:] + v[:-1]
        else:
            v[0], v[1] = v[1], v[0]
    return v


def is_sorted_root(v, m):
    return [0 if C.is_zero(x) else x for x in v] == list(range(1, m + 1)) + [0] * (len(v) - m)


def window_ranks(vec, f, cut, m):
    """Target rank of the element at each window index; zeros take zero targets in window order."""
    n = len(vec)
    seq, zw = [None] * n, []
    for p, x in enumerate(vec):
        w = (p - cut) % n
        if C.is_zero(x):
            zw.append(w)
        else:
            seq[w] = (f + x - 1 - cut) % n
    for w, t in zip(sorted(zw), sorted((f + m + i - cut) % n for i in range(n - m))):
        seq[w] = t
    return seq


def H(seq, j, s):
    return sum(1 for i in range(j) if seq[i] < s)


def dominated(P, Q):
    n = len(P)
    return all(H(P, j, s) >= H(Q, j, s) for j in range(n + 1) for s in range(n + 1))


def inv(seq):
    return sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] > seq[j])


def sigma_at(seq, islabel, w0):
    r0 = seq[w0]
    return sum(1 for w in range(len(seq)) if islabel[w] and ((w < w0 and seq[w] > r0) or (w > w0 and seq[w] < r0)))


def zero_linear_positions(vec):
    return [p for p, x in enumerate(vec) if C.is_zero(x)]


def compare_run(vecP, seqP, seqQ, word, cut, check_steps):
    """Rotations as given; X only on a descending pair of P.  Q is swapped unconditionally.
    Returns (word on P, final visible P, swaps, Q descending at every swap, step failures)."""
    n = len(vecP)
    P, Q, vals = list(seqP), list(seqQ), list(vecP)
    c, out, swaps, qdesc, bad = 0, [], 0, True, 0
    for ch in word:
        if ch == 'X':
            w = (c - cut) % n
            if w == n - 1:
                raise AssertionError('swap across the cut')
            if check_steps:
                want = [min(H(P, w, s) + 1, H(P, w + 2, s)) for s in range(n + 1)]
            if Q[w] < Q[w + 1]:
                qdesc = False
            Q[w], Q[w + 1] = Q[w + 1], Q[w]
            if P[w] > P[w + 1]:
                P[w], P[w + 1] = P[w + 1], P[w]
                c2 = (c + 1) % n
                vals[c], vals[c2] = vals[c2], vals[c]
                out.append('X')
                swaps += 1
            if check_steps:
                if [H(P, w + 1, s) for s in range(n + 1)] != want:
                    bad += 1
                if any(H(P, w + 1, s) < H(Q, w + 1, s) for s in range(n + 1)):
                    bad += 1
        else:
            c = (c + 1) % n if ch == 'L' else (c - 1) % n
            out.append(ch)
    return ''.join(out), vals[c:] + vals[:c], swaps, qdesc, bad, P, Q


def normal_form(w):
    """Each rotation string between swaps replaced by its net power (formula (4) normal form)."""
    out = []
    for seg in w.split('X'):
        e = seg.count('L') - seg.count('R')
        out.append('L' * e if e >= 0 else 'R' * -e)
    return 'X'.join(out)


def own_project(state, word, dead):
    """Lemma 4 on linear visible vectors; checks the invariant after every letter."""
    a, zi = [], 0
    for x in state:
        if C.is_zero(x):
            a.append(('z', zi))
            zi += 1
        else:
            a.append(('l', x))
    kept = lambda t: not (t[0] == 'z' and t[1] in dead)  # noqa: E731
    b = [t for t in a if kept(t)]
    out, bad = [], 0
    for ch in word:
        if ch == 'L':
            if kept(a[0]):
                out.append('L')
                b = b[1:] + b[:1]
            a = a[1:] + a[:1]
        elif ch == 'R':
            if kept(a[-1]):
                out.append('R')
                b = b[-1:] + b[:-1]
            a = a[-1:] + a[:-1]
        else:
            if kept(a[0]) and kept(a[1]):
                out.append('X')
                b[0], b[1] = b[1], b[0]
            a[0], a[1] = a[1], a[0]
        if b != [t for t in a if kept(t)]:
            bad += 1
    return ''.join(out), bad


# ------------------------------------------------ instance builders
def ref_state(m, k, rng, refine_blocks=0, origin=None):
    labels, mask = random_family(m, k, rng)
    base = C.base_vector(labels, mask)
    if origin is None:
        origin = [1] * k
        for j in rng.sample(range(k), refine_blocks):
            origin[j] = 2
    state = C.refine(base, origin)
    _, _, blocks = C.parse_state(state)
    return state, origin, blocks


def some_word(tab, state, rng, pre):
    if not pre:
        return geodesic(tab, tuple(state), rng)
    while True:
        ch = rng.choice('LRX')
        if not (ch == 'X' and C.is_zero(state[0]) and C.is_zero(state[1])):
            return ch + geodesic(tab, step(tuple(state), ch), rng)


def exact_cuts(state, word, picks, m, stats):
    prof = C.Profile(state, word, picks)
    n, out = prof.n, []
    zl = zero_linear_positions(state)
    for cut in range(n):
        if (cut - 1) % n in prof.used_edges:
            continue
        seq = window_ranks(state, prof.final_cursor, cut, m)
        if inv(seq) != prof.q:
            continue
        isl = [not C.is_zero(state[(w + cut) % n]) for w in range(n)]
        sq = [sigma_at(seq, isl, (zl[p] - cut) % n) for p in prof.picks]
        stats['A_eq_sigma' if sq == list(prof.A) else 'A_ne_sigma'] += 1
        out.append(cut)
    return prof, out


def bruhat_P(state, seq, f, cut, m, rng, moves):
    """Apply `moves` inversion-reducing label-label transpositions to Q's window ranks."""
    n = len(state)
    isl = [not C.is_zero(state[(w + cut) % n]) for w in range(n)]
    s = list(seq)
    for _ in range(moves):
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if isl[i] and isl[j] and s[i] > s[j]]
        if not pairs:
            break
        i, j = rng.choice(pairs)
        s[i], s[j] = s[j], s[i]
    P = list(state)
    for w in range(n):
        if isl[w]:
            P[(w + cut) % n] = (s[w] + cut - f) % n + 1
    return P


def relabel(state, rng):
    labs = [x for x in state if not C.is_zero(x)]
    rng.shuffle(labs)
    it = iter(labs)
    return [x if C.is_zero(x) else next(it) for x in state]


# ------------------------------------------------ Part T
def check_transfer(tab, m, Q, W, picks, cut, P, stats, zbudget):
    prof = C.Profile(Q, W, picks)
    n, f = prof.n, prof.final_cursor
    seqQ, seqP = window_ranks(Q, f, cut, m), window_ranks(P, f, cut, m)
    if not dominated(seqP, seqQ):
        stats['P_not_dominated_input'] += 1
        return
    # lrx_m's (11) vs this file's (11)
    base, beta, ip = C.Reference(Q, W, picks).transfer(P, cut)
    zl = zero_linear_positions(Q)
    isl = [not C.is_zero(Q[(w + cut) % n]) for w in range(n)]
    sQ = [sigma_at(seqQ, isl, (zl[p] - cut) % n) for p in picks]
    sP = [sigma_at(seqP, isl, (zl[p] - cut) % n) for p in picks]
    own_base = prof.base - inv(seqQ) + inv(seqP)
    own_beta = [prof.beta[j] - sQ[j] + sP[j] for j in range(prof.k)]
    if (own_base, own_beta, inv(seqP)) != (base, list(beta), ip):
        stats['fail_eq11_mismatch'] += 1
    stats['sigmaP_le_sigmaQ' if all(a <= b for a, b in zip(sP, sQ)) else 'sigmaP_gt_sigmaQ'] += 1
    for z in z_vectors(prof.k, zbudget):
        w = prof.lift(z)
        Qz, Pz = C.stretch(Q, picks, z), C.stretch(P, picks, z)
        pos, nz = C.stretch_posmap(Q, picks, z)
        cz = pos[cut] if cut < n else 0
        fz = (w.count('L') - w.count('R')) % nz
        sQz, sPz = window_ranks(Qz, fz, cz, m), window_ranks(Pz, fz, cz, m)
        if not dominated(sPz, sQz):
            stats['fail_stretched_domination'] += 1
            continue
        if inv(sPz) != inv(seqP) + sum(a * t for a, t in zip(sP, z)):
            stats['fail_inv_stretch_formula'] += 1
        word, fin, swaps, qdesc, bad, Pend, Qend = compare_run(Pz, sPz, sQz, w, cz, check_steps=True)
        stats['steps_checked'] += w.count('X')
        if bad:
            stats['fail_step_invariant_9_10'] += bad
        if not qdesc or Qend != sorted(Qend) or w.count('X') != inv(sQz):
            stats['fail_reference_not_inversion_exact'] += 1
        if not is_sorted_root(fin, m) or not is_sorted_root(execute(Pz, word), m) or Pend != sorted(Pend):
            stats['fail_comparison_does_not_sort'] += 1
        if swaps != inv(sPz):
            stats['fail_swaps_ne_inv'] += 1
        eleven = base + sum(b * t for b, t in zip(beta, z))
        if len(word) > eleven:
            stats['fail_length_gt_11'] += 1
        if prof.same_sign and len(word) != eleven:
            stats['fail_same_sign_length_ne_11'] += 1
        d = tab.dist(Pz)
        if d > len(word) or d > eleven:
            stats['fail_d_gt_length'] += 1
        stats['points'] += 1
        stats['slack'][eleven - d] += 1


def part_t(tab, rng):
    per = collections.Counter()
    stats = collections.Counter()
    stats['slack'] = collections.Counter()
    neg = collections.Counter()
    plan = ([('bruhat', 9, k, 0, False) for k in (1, 2, 3, 4, 5) for _ in range(40)]
            + [('bruhat-ref', 9, k, 1, False) for k in (1, 2, 3) for _ in range(15)]
            + [('filter', 9, k, 0, False) for k in (2, 3, 4) for _ in range(15)]
            + [('pre', 9, k, 0, True) for k in (2, 3, 4) for _ in range(10)]
            + [('bruhat', 10, 2, 0, False) for _ in range(80)]
            + [('bruhat', 10, 3, 0, False) for _ in range(60)]
            + [('bruhat-ref', 10, 1, 1, False) for _ in range(30)]
            + [('bruhat-ref', 10, 2, 1, False) for _ in range(30)]
            + [('filter', 10, 2, 0, False) for _ in range(20)])
    tries = collections.Counter()
    for kind, m, k, nref, pre in plan:
        for _ in range(200):
            Q, origin, blocks = ref_state(m, k, rng, nref)
            if len(Q) - m < RMIN[m]:
                continue
            picks = [rng.choice(b) for b in blocks]
            W = some_word(tab, Q, rng, pre)
            prof, cuts = exact_cuts(Q, W, picks, m, stats)
            tries[m] += 1
            if not cuts:
                continue
            cut = rng.choice(cuts)
            seqQ = window_ranks(Q, prof.final_cursor, cut, m)
            if kind.startswith('filter'):
                for _ in range(60):
                    P = relabel(Q, rng)
                    if P != Q and dominated(window_ranks(P, prof.final_cursor, cut, m), seqQ):
                        break
                else:
                    continue
            else:
                P = bruhat_P(Q, seqQ, prof.final_cursor, cut, m, rng, rng.randint(1, 4))
            break
        else:
            raise SystemExit('no instance for %s' % ((kind, m, k),))
        check_transfer(tab, m, Q, W, picks, cut, P, stats, RMAX[m] - (len(Q) - m))
        per[kind, m] += 1
        # negative control: a random relabelling that is NOT <= Q
        for _ in range(20):
            Pn = relabel(Q, rng)
            sPn = window_ranks(Pn, prof.final_cursor, cut, m)
            if not dominated(sPn, seqQ):
                _, fin, _, _, _, _, _ = compare_run(Pn, sPn, seqQ, W, cut, False)
                neg['sorts' if is_sorted_root(fin, m) else 'fails'] += 1
                break
    return per, stats, neg, tries


# ------------------------------------------------ Part P
def check_projection(tab, m, parent, W, dead, stats, rng):
    child, cw, keep = C.project(parent, W, dead)
    own, bad = own_project(parent, W, dead)
    if own != cw:
        stats['fail_word_mismatch_lrx_m'] += 1
    stats['letters_checked'] += len(W)
    if bad:
        stats['fail_step_invariant'] += bad
    if not is_sorted_root(execute(child, cw), m):
        stats['fail_projected_does_not_sort'] += 1
        return
    if len(cw) > len(W):
        stats['fail_projected_longer'] += 1
    # picks: parent picks on kept atoms where possible; child picks are their images
    _, _, pblocks = C.parse_state(parent)
    _, _, cblocks = C.parse_state(child)
    pz = zero_linear_positions(parent)
    kept_zero_ids = [i for i in range(len(pz)) if i not in dead]  # parent zero id -> child zero id by order
    to_child = {pid: cid for cid, pid in enumerate(kept_zero_ids)}
    ppicks, cpicks = [], [None] * len(cblocks)
    for b in pblocks:
        alive = [i for i in b if i not in dead]
        ppicks.append(rng.choice(alive) if alive else b[0])
    for p in ppicks:
        if p in to_child:
            cid = to_child[p]
            for j, cb in enumerate(cblocks):
                if cid in cb:
                    cpicks[j] = cid
    if None in cpicks:
        raise AssertionError('child block without a picked atom')
    pprof = C.Profile(parent, W, ppicks)
    cprof = C.Profile(child, cw, cpicks)
    # manuscript side claim (lines 369-371): coefficients do not increase
    cmap = [ppicks.index(kept_zero_ids[c]) for c in cpicks]
    stats['base_noninc' if cprof.base <= pprof.base else 'base_increases'] += 1
    stats['slopes_noninc' if all(cprof.beta[j] <= pprof.beta[cmap[j]] for j in range(cprof.k))
          else 'slopes_increase'] += 1
    for z in z_vectors(cprof.k, RMAX[m] - (len(child) - m)):
        zp = [0] * pprof.k
        for j, t in enumerate(z):
            zp[cmap[j]] = t
        lw = pprof.lift(zp)
        Pz = C.stretch(parent, ppicks, zp)
        # stretched ids of deleted (unit) atoms
        sid, dz = 0, set()
        for i in range(len(pz)):
            if i in dead:
                dz.add(sid)
            sid += 1 + (zp[ppicks.index(i)] if i in ppicks else 0)
        ch_z, pw, _ = C.project(Pz, lw, dz)
        Cz = C.stretch(child, cpicks, z)
        if [0 if C.is_zero(x) else x for x in ch_z] != [0 if C.is_zero(x) else x for x in Cz]:
            stats['fail_stretched_child_mismatch'] += 1
            continue
        if normal_form(pw) != normal_form(cprof.lift(z)):
            stats['fail_commute_normal_form'] += 1
        if pw != cprof.lift(z):
            stats['commute_letterwise_differs'] += 1
        if not is_sorted_root(execute(Cz, pw), m):
            stats['fail_proj_lift_does_not_sort'] += 1
        if not is_sorted_root(execute(Cz, cprof.lift(z)), m) or len(cprof.lift(z)) != cprof.exact_len(z):
            stats['fail_child_lift'] += 1
        stats['Fchild_le_Fparent' if cprof.exact_len(z) <= pprof.exact_len(zp) else 'Fchild_gt_Fparent'] += 1
        d = tab.dist(Cz)
        if d > cprof.exact_len(z) or d > len(pw) or d > cprof.affine(z):
            stats['fail_d_gt_child_cost'] += 1
        stats['points'] += 1
        stats['slack'][cprof.affine(z) - d] += 1


def part_p(tab, rng):
    per = collections.Counter()
    stats = collections.Counter()
    stats['slack'] = collections.Counter()
    plan = ([('unit', 9, k, 0, False) for k in (2, 3, 4, 5, 6) for _ in range(40)]
            + [('ref', 9, k, 1, False) for k in (1, 2, 3, 4) for _ in range(10)]
            + [('pre', 9, k, 0, True) for k in (2, 3, 4, 5) for _ in range(8)]
            + [('unit', 10, 3, 0, False) for _ in range(80)]
            + [('ref', 10, 2, 1, False) for _ in range(60)]
            + [('ref3', 10, 1, 0, False) for _ in range(40)]
            + [('pre', 10, 3, 0, True) for _ in range(20)])
    for kind, m, k, nref, pre in plan:
        origin = [3] if kind == 'ref3' else None
        parent, origin, blocks = ref_state(m, k, rng, nref, origin)
        W = some_word(tab, parent, rng, pre)
        nz = len(parent) - m
        while True:  # nonempty proper deletion, child keeps >= RMIN zeros
            dead = set(i for i in range(nz) if rng.random() < 0.5)
            if dead and nz - len(dead) >= RMIN[m]:
                break
            if nz - 1 < RMIN[m]:
                raise SystemExit('parent too small')
        check_projection(tab, m, parent, W, dead, stats, rng)
        per[kind, m] += 1
    return per, stats


def part_pt(tab, rng):
    """Projected reference, then transfer (the route of the m=8 package's union audit)."""
    per = collections.Counter()
    stats = collections.Counter()
    stats['slack'] = collections.Counter()
    m = 9
    for k in (3, 4, 5, 6):
        done = 0
        while done < 15:
            parent, _, pblocks = ref_state(m, k, rng)
            W = geodesic(tab, tuple(parent), rng)
            keepb = sorted(rng.sample(range(k), rng.randint(1, k - 1)))
            dead = set(i for j, b in enumerate(pblocks) if j not in keepb for i in b)
            Q, cw, _ = C.project(parent, W, dead)
            _, _, blocks = C.parse_state(Q)
            picks = [b[0] for b in blocks]
            prof, cuts = exact_cuts(Q, cw, picks, m, stats)
            if not cuts:
                continue
            cut = rng.choice(cuts)
            seqQ = window_ranks(Q, prof.final_cursor, cut, m)
            P = bruhat_P(Q, seqQ, prof.final_cursor, cut, m, rng, rng.randint(1, 4))
            check_transfer(tab, m, Q, cw, picks, cut, P, stats, RMAX[m] - (len(Q) - m))
            per['proj+trans', m, k] += 1
            done += 1
    return per, stats


def resource_terms(state, word):
    """Section 7 (lines 392-415): A_j, B_j, F_j and the incremental resource of every zero atom."""
    a, zi = [], 0
    for x in state:
        a.append(('z', zi) if C.is_zero(x) else ('l', x))
        zi += C.is_zero(x)
    nz = zi
    A, B, F, res = [0] * nz, [0] * nz, [0] * nz, [0] * nz
    prev = None
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else None
        first, second, last = a[0], a[1], a[-1]
        if ch == 'L':
            if first[0] == 'z':
                B[first[1]] += 1
                if prev != 'X':
                    res[first[1]] += 1
            a = a[1:] + a[:1]
        elif ch == 'R':
            if last[0] == 'z':
                B[last[1]] += 1
                res[last[1]] += 1
            if first[0] == 'z' and prev == 'X':
                res[first[1]] += 1
            a = a[-1:] + a[:-1]
        else:
            if first[0] == 'z':
                A[first[1]] += 1
                F[first[1]] += prev == 'R'
                res[first[1]] += 1 if prev == 'R' else 3
            if second[0] == 'z':
                A[second[1]] += 1
                F[second[1]] += nxt == 'L'
                res[second[1]] += 2
            a[0], a[1] = a[1], a[0]
        prev = ch
    return [3 * A[j] + B[j] - 2 * F[j] for j in range(nz)], res


def part_r(tab, rng):
    """beta_j = 3A_j + B_j - 2F_j and the increment table, on freely reduced shortest words."""
    per = collections.Counter()
    st = collections.Counter()
    plan = ([(9, k, nref) for k in (1, 2, 3, 4, 5) for nref in (0, 1) for _ in range(20)]
            + [(10, k, 1) for k in (1, 2) for _ in range(40)] + [(10, 2, 0) for _ in range(40)])
    for m, k, nref in plan:
        state, _, _ = ref_state(m, k, rng, nref)
        if len(state) - m < RMIN[m] or len(state) - m > RMAX[m]:
            continue
        w = geodesic(tab, tuple(state), rng)
        if any(t in w for t in ('LR', 'RL', 'XX')):
            st['not_reduced'] += 1
            continue
        beta = C.Profile(state, w, each_zero=True).beta
        formula, res = resource_terms(state, w)
        st['atoms'] += len(beta)
        if formula != list(beta):
            st['fail_beta_3A_B_2F'] += 1
        if res != list(beta):
            st['fail_increment_table'] += 1
        per[m] += 1
    return per, st


def fails(stats):
    return {k: v for k, v in stats.items() if k.startswith('fail') and v}


def hist(c):
    return ' '.join('%d:%d' % (k, c[k]) for k in sorted(c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=260926)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tab = Tables()
    t0 = time.time()
    total_fail = 0

    per, st, neg, tries = part_t(tab, rng)
    print('Part T  Lemma 3 + (11) against exact distances (seed %d)' % args.seed)
    for key in sorted(per):
        print('  %-11s m=%-2d instances %d' % (key[0], key[1], per[key]))
    print('  instances per m: m=9 %d, m=10 %d ; reference attempts (family,word) per m: %s'
          % (sum(v for (_, m), v in per.items() if m == 9), sum(v for (_, m), v in per.items() if m == 10), dict(tries)))
    print('  stretched points z tested %d ; comparison X-steps checked against (9),(10) %d'
          % (st['points'], st['steps_checked']))
    print('  q = inv(Q) cuts: A_j = sigma_j(Q) holds %d, fails %d' % (st['A_eq_sigma'], st['A_ne_sigma']))
    print('  sigma_j(P) <= sigma_j(Q) (manuscript line 335): holds %d, fails %d'
          % (st['sigmaP_le_sigmaQ'], st['sigmaP_gt_sigmaQ']))
    print('  failures: %s' % (fails(st) or 0))
    print('  slack (11)(z) - d(E_z P): %s' % hist(st['slack']))
    print('  negative control (P not <= Q, z=0): comparison run fails to sort %d, sorts anyway %d'
          % (neg['fails'], neg['sorts']))
    total_fail += sum(fails(st).values())

    per, st = part_pt(tab, rng)
    print('\nPart T2 projected reference then transfer (m=9)')
    print('  instances %s ; points %d ; X-steps %d' % (dict(per), st['points'], st['steps_checked']))
    print('  A_j = sigma_j(Q) holds %d, fails %d ; failures: %s'
          % (st['A_eq_sigma'], st['A_ne_sigma'], fails(st) or 0))
    print('  slack (11)(z) - d(E_z P): %s' % hist(st['slack']))
    total_fail += sum(fails(st).values())

    per, st = part_p(tab, rng)
    print('\nPart P  Lemma 4 projection against exact distances')
    for key in sorted(per):
        print('  %-5s m=%-2d instances %d' % (key[0], key[1], per[key]))
    print('  instances per m: m=9 %d, m=10 %d ; parent letters with invariant checked %d ; child points z %d'
          % (sum(v for (_, m), v in per.items() if m == 9), sum(v for (_, m), v in per.items() if m == 10),
             st['letters_checked'], st['points']))
    print('  proj(lift_z W) vs lift_z(proj W): normal forms differ at %d points; raw words differ at %d '
          '(lift writes net rotations)' % (st['fail_commute_normal_form'], st['commute_letterwise_differs']))
    print('  side claims (not used for soundness): base non-increasing %d/%d, slopes non-increasing %d/%d, '
          'F_child(z) <= F_parent(z) %d/%d'
          % (st['base_noninc'], st['base_noninc'] + st['base_increases'],
             st['slopes_noninc'], st['slopes_noninc'] + st['slopes_increase'],
             st['Fchild_le_Fparent'], st['Fchild_le_Fparent'] + st['Fchild_gt_Fparent']))
    print('  failures: %s' % (fails(st) or 0))
    print('  slack (B_child + beta_child.z) - d(E_z child): %s' % hist(st['slack']))
    total_fail += sum(fails(st).values())

    per, st = part_r(tab, rng)
    print('\nPart R  section 7 resource formula beta_j = 3A_j + B_j - 2F_j and increment table (lines 392-425)')
    print('  words: m=9 %d, m=10 %d ; zero atoms %d ; failures: %s'
          % (per[9], per[10], st['atoms'], fails(st) or 0))
    total_fail += sum(fails(st).values())

    print('\n%.1f s' % (time.time() - t0))
    print('RESULT: %s (%d violations)' % ('PASS' if total_fail == 0 else 'FAIL', total_fail))
    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
