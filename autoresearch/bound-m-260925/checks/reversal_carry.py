"""Carry-across words for the middle band of k=2 reversal masks (m..1){0,g}: re-check only.

Offline. No provider calls, no LLM-generated code, no commits. This script never writes a file (so it cannot
overwrite anything) and never searches. It re-checks reversal-carry-words.json:

  1. every stored CERTIFIED output: bound3_evaluator.score_output must return CERTIFIED, bound3_audit.audit_claim
     must return (True, 'ok'), and every leaf word must sort its refined base under lrx_m.run_naive and lrx_m.run;
     words stored with generator parameters are re-derived letter by letter (word_K below);
  2. the closed form word_M(m, g, side): for m = 14..40 every band value g where the single word meets criterion
     (7) is scored by the evaluator and the audit; for m = 41..60 (or --to) by replay and lrx_m.mixture_criterion;
     the covered g-sets must equal the stored ones.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_carry.py            # about 1 min
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_carry.py --quick    # stored rows only
"""
import json
import sys
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family

HERE = Path(__file__).resolve().parent
DATA = HERE / 'reversal-carry-words.json'


# ------------------------------------------------------------------ generator (stdlib)
def sched_word2(state, cores, fin):
    """Insertion cores with explicit side schedules and one cut per core. Physical model of lrx_m: cells 0..n-1,
    cursor c = 0, L: c+1, R: c-1, X swaps cells c, c+1. Core (seed, sides, t) sorts into the order t+1..m, 0, 1..t
    (zeros tied, so zeros never swap): 'r' inserts cell hi+1 by carrying it left past the core elements of larger
    rank (X (RX)^(s-1)), 'l' inserts cell lo-1 by carrying it right past those of smaller rank (X (LX)^(s-1)).
    The cursor moves between sweeps by the shorter way round. Then a walk (fin) to label 1."""
    n = len(state)
    m = sum(1 for x in state if x)
    cell, w, c = list(state), [], 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    for seed, sides, t in cores:
        order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
        rk = {x: i for i, x in enumerate(order)}
        lo = hi = seed
        ln = 1
        for side in sides:
            if side == 'r':
                j = (hi + 1) % n
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
    i = cell.index(1)
    if [cell[(i + x) % n] for x in range(m)] != list(range(1, m + 1)) or any(cell[(i + m + x) % n] for x in range(n - m)):
        return None
    w.append('L' * ((i - c) % n) if fin == 'L' else 'R' * ((c - i) % n))
    return ''.join(w)


def core2_canon(side, m, g, p, q, seed, first):
    """Alternating side schedule for core 2 (cells q+1 .. m+1-p, i.e. [A_2] Zg [B_2]), extended over B_c = 1..p
    ('lo') or A_c = m..m-q+1 ('hi'); absorbing Zg (a free insertion) does not use up a turn."""
    n = m + 2
    lo2, hi2 = q + 1, n - p - 1
    zg = g + 1
    lcells = list(range(seed - 1, lo2 - 1, -1)) + ([(lo2 - 1 - i) % n for i in range(p)] if side == 'lo' else [])
    rcells = list(range(seed + 1, hi2 + 1)) + ([(hi2 + 1 + i) % n for i in range(q)] if side == 'hi' else [])
    s, li, ri, cur = '', 0, 0, first
    while li < len(lcells) or ri < len(rcells):
        if cur == 'l' and li < len(lcells) or ri == len(rcells):
            s += 'l'
            li += 1
            if lcells[li - 1] == zg and li < len(lcells):
                s += 'l'
                li += 1
            cur = 'r'
        else:
            s += 'r'
            ri += 1
            if rcells[ri - 1] == zg and ri < len(rcells):
                s += 'r'
                ri += 1
            cur = 'l'
    return s


def unit_state(m, g):
    return C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)


def word_K(m, g, side, p, q, s1, seed, s2, fin='L'):
    """Carry word on the unit base of (m..1){0,g}.
    core 1 = zero-core seeded at cell 0 (Z0), cut p, schedule s1: q large labels m..m-q+1 are carried leftwards
             across Z0 and p small labels 1..p rightwards (two-sided, 2 per crossing inside a sweep);
    core 2 = zigzag seeded at `seed` over [A_2] Zg [B_2] with schedule s2 and cut m ('lo': Zg sorts to the left end
             and then walks left over B_c) or cut p ('hi': Zg sorts to the right end and walks right over A_c);
    then a walk fin to label 1."""
    return sched_word2(unit_state(m, g), [(0, s1, p), (seed, s2, m if side == 'lo' else p)], fin)


def params_M(m, side):
    """Closed-form parameters (p, q, s1, seed, first) by m mod 4; j = floor(m/4)."""
    j, r = m // 4, m % 4
    if side == 'lo':
        p, q, seed, first = {0: (j - 2, j, 2 * j + 2, 'r'), 1: (j - 1, j, 2 * j + 2, 'r'),
                             2: (j - 1, j, 2 * j + 3, 'l'), 3: (j - 2, j + 1, 2 * j + 4, 'r')}[r]
        return p, q, 'r' * (q - p) + 'lr' * p, seed, first
    p, q, seed, first = {0: (j, j - 2, 2 * j, 'l'), 1: (j, j - 1, 2 * j + 1, 'l'),
                         2: (j, j - 1, 2 * j + 1, 'r'), 3: (j + 1, j - 2, 2 * j + 1, 'l')}[r]
    return p, q, 'l' * (p - q) + 'rl' * q, seed, first


def word_M(m, g, side):
    p, q, s1, seed, first = params_M(m, side)
    if min(p, q) < 0 or p > m - g or q > g:
        return None
    return word_K(m, g, side, p, q, s1, seed, core2_canon(side, m, g, p, q, seed, first), 'L')


# ------------------------------------------------------------------ checks
def leaves(out):
    def walk(node):
        if 'words' in node:
            yield node['words'], node.get('origins', [1, 1])
        else:
            yield from walk(node['le'])
            yield from walk(node['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


def replay_ok(fam, out):
    return all(C.is_root(C.run_naive(C.refine(fam['unit_base'], o), w)) and
               C.is_root(C.run(C.refine(fam['unit_base'], o), w)) for ws, o in leaves(out) for w in ws)


def check_row(m, g, out):
    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
    r = score_output(fam, out)
    au = tuple(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
    return r, au, replay_ok(fam, out)


def band(m):
    return range(m // 4 + 1, m - m // 4)


def closed_form_rows(m):
    """-> {side: [(g, B - T, beta)]} for band g where the single word meets criterion (7)."""
    s, T = m - 2, C.budget(m, 2)
    res = {}
    for side in ('lo', 'hi'):
        res[side] = []
        for g in band(m):
            w = word_M(m, g, side)
            if not w:
                continue
            p = C.Profile(unit_state(m, g), w)
            ok, B, beta = C.mixture_criterion([(p.base, p.beta)], [1], 2, m=m)
            if ok:
                res[side].append((g, p.base - T, list(p.beta)))
    return res


def main():
    res = json.loads(DATA.read_text())
    bad = []
    for row in res['certified']:
        r, au, rep = check_row(row['m'], row['g'], row['output'])
        der = None
        if row.get('params'):
            got = [word_K(row['m'], row['g'], *p) if p[0] in ('lo', 'hi') else None for p in row['params']]
            ws = [w for ws_, _ in leaves(row['output']) for w in ws_]
            der = all(x is None or x == w for x, w in zip(got, ws)) and any(x is not None for x in got)
        ok = r['status'] == 'CERTIFIED' and au == (True, 'ok') and rep and der is not False
        print('m=%-2d {0,%-2d} %-24s %s leaves=%s lhs=%s audit=%s replay=%s rederived=%s' % (
            row['m'], row['g'], row['source'], r['status'], r['n_leaves'], [x['lhs'] for x in r['leaves']], au, rep, der))
        if not ok:
            bad.append((row['m'], row['g'], row['source']))
    if '--quick' not in sys.argv:
        top = int(sys.argv[sys.argv.index('--to') + 1]) if '--to' in sys.argv else 60
        cov = {int(k): v for k, v in res['closed_form']['coverage'].items()}
        n_eval = n_rep = 0
        for m in range(14, top + 1):
            rows = closed_form_rows(m)
            got = {side: [x[0] for x in rows[side]] for side in rows}
            if m in cov and got != cov[m]:
                bad.append(('closed form coverage', m, got, cov[m]))
            for side in rows:
                for g, _, _ in rows[side]:
                    w = word_M(m, g, side)
                    fam = make_family(list(range(m, 0, -1)), 1 | 1 << g)
                    if not replay_ok(fam, {'words': [w]}):
                        bad.append(('closed form replay', m, g, side))
                    if m <= 40:
                        r, au, _ = check_row(m, g, {'words': [w]})
                        n_eval += 1
                        if r['status'] != 'CERTIFIED' or au != (True, 'ok'):
                            bad.append(('closed form evaluator/audit', m, g, side, r['status'], au))
                    else:
                        n_rep += 1
            print('closed form m=%d: lo %s hi %s' % (m, got['lo'], got['hi']))
        print('closed form: %d rows scored by evaluator + audit (m <= 40), %d rows by replay + criterion (7)' % (
            n_eval, n_rep))
    print('problems:', bad or 'none')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
