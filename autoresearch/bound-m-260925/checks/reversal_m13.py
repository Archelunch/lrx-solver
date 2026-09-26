"""Two-core words for the reversal with two outer zeros, (0, m, m-1, ..., 1, 0), m >= 9.

Offline construction (no tables, no provider calls, no generated code). Every word is replayed literally with
lrx_m.run_naive and lrx_m.run, priced by lrx_m.Profile (Lemma 1, the group's), scored by
bound3_evaluator.score_output on family (m..1){0,m} and every CERTIFIED row is re-checked by the independent
bound3_audit.audit_claim. Writes reversal-m13-words.json next to this file (refuses to overwrite).

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_m13.py
"""
import json
import sys
import time
from fractions import Fraction as Fr
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family

HERE = Path(__file__).resolve().parent
OUT = HERE / 'reversal-m13-words.json'


# ---------------------------------------------------------------- generator (pure function of m and a, stdlib only)
def word_C(m, a):
    """Two-core word for (0, m, ..., 1, 0).  Physical model: cells 0..n-1 on a cycle, cursor c (start 0),
    L: c+1, R: c-1, X swaps cells c, c+1.  A core is a cyclic arc of cells, grown by alternately carrying its
    right neighbour across the whole core to its left end ('r', letters X (RX)^len-1) and its left neighbour
    to its right end ('l', letters X (LX)^len-1), the cursor stepping one cell between sweeps.
      core 1 = the zero block (cells n-1, 0), grown by a labels, first 'r' (so ceil(a/2) large labels
               m, m-1, ... cross the zeros leftwards and floor(a/2) small labels 1, 2, ... rightwards);
      core 2 = the complementary arc of the r = m-a remaining labels, grown from one cell by r-1 sweeps,
               first 'r' if r is even else 'l', the start cell chosen so that core 2 ends exactly on that arc;
      then R steps until the cursor is on label 1."""
    n, r = m + 2, m - a
    cell = [0] + list(range(m, 0, -1)) + [0]
    st = {'c': 0, 'w': []}

    def step(ch):
        st['w'].append(ch)
        c = st['c']
        if ch == 'L':
            st['c'] = (c + 1) % n
        elif ch == 'R':
            st['c'] = (c - 1) % n
        else:
            j = (c + 1) % n
            cell[c], cell[j] = cell[j], cell[c]

    def goto(p, d=None):
        f, b = (p - st['c']) % n, (st['c'] - p) % n
        d = d or ('L' if f <= b else 'R')
        for _ in range(f if d == 'L' else b):
            step(d)

    def grow(lo, hi, side, sweeps):
        for _ in range(sweeps):
            ln = (hi - lo) % n + 1
            if side == 'r':
                goto(hi)
                step('X')
                for _ in range(ln - 1):
                    step('R')
                    step('X')
                hi = (hi + 1) % n
            else:
                goto((lo - 1) % n)
                step('X')
                for _ in range(ln - 1):
                    step('L')
                    step('X')
                lo = (lo - 1) % n
            side = 'l' if side == 'r' else 'r'

    q, p = (a + 1) // 2, a // 2                    # labels crossing the zeros leftwards / rightwards
    grow(n - 1, 0, 'r', a)
    if r > 1:
        first = 'r' if r % 2 == 0 else 'l'
        right = (r - 1 + (first == 'r')) // 2      # 'r' sweeps of core 2 extend its right end
        start = n - 2 - p - right                  # core 2 then covers cells 1+q .. n-2-p exactly
        grow(start, start, first, r - 1)
    goto(cell.index(1), 'R')
    return ''.join(st['w'])


def certificate_words(m):
    """Odd m: one word, a = (m-3)/2.  Even m: a = (m-2)/2 and a = (m-4)/2 (the LP weights them 1/2, 1/2)."""
    return [word_C(m, (m - 3) // 2)] if m % 2 else [word_C(m, (m - 2) // 2), word_C(m, (m - 4) // 2)]


# ---------------------------------------------------------------- checks
def unit(m):
    return [0] + list(range(m, 0, -1)) + [0]


def replay(m, w):
    v = unit(m)
    return C.is_root(C.run_naive(v, w)) and C.is_root(C.run(v, w))


def main():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    t0 = time.time()
    res = {'schema': 'lrx-reversal-m13-v1', 'date': '2026-09-26',
           'state': '(0, m, m-1, ..., 1, 0), family (m..1){0,m}, mask 1 | 1<<m, T = m(m+1)/2 + m - 2, s = m - 2',
           'semantics': 'word sorts the state to (1..m,0,0); L: (v1..vn)->(v2..vn,v1), R = L^-1, X swaps v1,v2 '
                        '(integrations/lrx_m.run_naive); replayed with run_naive and run',
           'generator': 'word_C(m, a) in checks/reversal_m13.py', 'pool_scan': {}, 'certificates': {}}
    # 1. the whole parametrized family a = 0..m at m = 9..20: length - T, slopes, and the LP over all of it
    for m in range(9, 21):
        fam = make_family(list(range(m, 0, -1)), 1 | 1 << m)
        T, pool = fam['budget_unit'], []
        rows = []
        for a in range(m + 1):
            w = word_C(m, a)
            if not replay(m, w):
                rows.append({'a': a, 'sorts': False})
                continue
            p = C.Profile(fam['unit_base'], w)
            rows.append({'a': a, 'sorts': True, 'length': len(w), 'length_minus_T': len(w) - T, 'base': p.base,
                         'beta': p.beta, 'A': p.A, 'same_sign': p.same_sign})
            pool.append(w)
        r = score_output(fam, {'words': pool})
        lf = r['leaves'][0]
        res['pool_scan'][m] = {'T': T, 's': m - 2, 'rows': rows, 'pool_status': r['status'], 'pool_gap': r['gap'],
                               'pool_support': [[x['weight'], x['base'], x['beta']] for x in lf['support']]}
        print('pool m=%d: %s gap %s support %s' % (m, r['status'], r['gap'], res['pool_scan'][m]['pool_support']),
              flush=True)
    # 2. the fixed certificate (1 or 2 words) at m = 9..40: evaluator + independent audit + criterion (7) re-check
    for m in range(9, 41):
        fam = make_family(list(range(m, 0, -1)), 1 | 1 << m)
        ws = certificate_words(m)
        out = {'words': ws}
        r = score_output(fam, out)
        lf = r['leaves'][0]
        sup = [[x['weight'], x['base'], x['beta']] for x in lf['support']]
        row = {'family': fam['id'], 'T': fam['budget_unit'], 's': m - 2, 'words': ws,
               'lengths': [len(w) for w in ws], 'replay_ok': all(replay(m, w) for w in ws),
               'status': r['status'], 'gap': r['gap'], 'lhs': lf['lhs'], 'support': sup}
        if r['status'] == 'CERTIFIED':
            row['audit'] = list(audit_claim(fam, r['output'], r['certificate']))
            row['criterion7_recheck'] = C.mixture_criterion([(b, bt) for _, b, bt in sup], [Fr(x) for x, _, _ in sup],
                                                            2, m=m)[0]
        res['certificates'][m] = row
        print('cert m=%d T=%d: %s gap %s lhs %s support %s audit %s' % (
            m, row['T'], r['status'], r['gap'], row['lhs'], sup, row.get('audit')), flush=True)
    # 3. replay-only range for the certificate words and their closed forms
    bad = []
    for m in range(9, 201):
        T = C.budget(m, 2)
        for w in certificate_words(m):
            p = C.Profile(unit(m), w)
            a = p.A[0]
            want_len = T - 1 if (m % 2 or a == (m - 2) // 2) else T + 1
            if not (replay(m, w) and len(w) == p.base == want_len and p.beta == [2 * a + 1, 2 * a]
                    and p.A == [a, a] and p.same_sign):
                bad.append(m)
    res['closed_form_replay_m9_200'] = {
        'claim': 'odd m: len = base = T-1, beta = (m-2, m-3); even m: a=(m-2)/2 gives T-1, (m-1, m-2) and '
                 'a=(m-4)/2 gives T+1, (m-3, m-4); A = (a, a); same-sign', 'failures': bad}
    print('closed forms m=9..200 failures:', bad)
    res['seconds'] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print('wrote', OUT.relative_to(HERE.parents[2]), res['seconds'], 's')


if __name__ == '__main__':
    main()
