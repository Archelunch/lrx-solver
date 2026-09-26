"""Middle band of k=2 reversal masks (m..1){0,g}: re-check of the stored words, trees and the exact negative.

Offline. No provider calls, no LLM-generated code, no commits. This script only re-checks
reversal-midband-words.json; it never writes a file (so it cannot overwrite anything) and never searches.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py            # < 10 s, no tables
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_midband.py --tables   # + exact negative (tables)

Checks:
  1. every stored CERTIFIED output: bound3_evaluator.score_output must return CERTIFIED, bound3_audit.audit_claim
     must return (True, 'ok'), and every leaf word must sort its refined base under lrx_m.run_naive and lrx_m.run;
  2. every word_S row: the stored support words are re-derived letter by letter from their parameters with word_S
     below (a pure stdlib function of (m, g, b, ds, schedule, fin));
  3. the dual certificate of the exact negative (m = 9, {0,4}, root leaf): the witness word has B + 3 beta_0 = 75;
     with --tables the exact oracle (reversal_midband_search/mb.py, A* over all reduced words, admissible table
     heuristics) is re-run and must return min B + 3 beta_0 = 75 >= T + 1 + 3(m-2) = 74; it also re-reads the
     exact unit distances of the (9,2) table.
"""
import json
import sys
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family

HERE = Path(__file__).resolve().parent
DATA = HERE / 'reversal-midband-words.json'


# ------------------------------------------------------------------ generator word_S (stdlib)
def sched_word(state, t, cores, fin, pre=''):
    """Insertion cores with explicit side schedules (core_word of reversal_orbit.py grows sides alternately; here
    each core has a string of sides). Physical model of lrx_m: cells 0..n-1, cursor c = 0, L: c+1, R: c-1,
    X swaps cells c, c+1. Target order from cut t: labels t+1..m, zeros (tied), labels 1..t. `pre` is executed
    literally first. A right step inserts cell hi+1 by carrying it left (X (RX)^(s-1)) past the s core elements
    of larger rank; a left step inserts cell lo-1 by carrying it right (X (LX)^(s-1)). Then a walk to label 1."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w, c = list(state), [], 0
    for ch in pre:
        if ch == 'L':
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
        else:
            j = (c + 1) % n
            cell[c], cell[j] = cell[j], cell[c]
        w.append(ch)

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    for seed, sides in cores:
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
    if [cell[(i + x) % n] for x in range(m)] != list(range(1, m + 1)):
        return None
    w.append('L' * ((i - c) % n) if fin == 'L' else 'R' * ((c - i) % n))
    return ''.join(w)


def word_S(m, g, b, ds, sc1, fin='L'):
    """(m..1){0,g}, unit base. Split: the b smallest labels form block 2 (with the gap-0 zero), labels m..b+1 form
    block 1 (with the gap-g zero, which a = m-g-b labels cross). Prefix RX (label 1 crosses the gap-0 zero), block-1
    core seeded at cell 1+ds with side schedule sc1 (length g+a), block-2 core seeded at cell n-b growing right b
    times, cut t = b, final walk fin."""
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
    a = m - g - b
    if a < 0 or len(sc1) != g + a:
        return None
    return sched_word(st, b, [(1 + ds, sc1), (m + 2 - b, 'r' * b)], fin, 'RX')


# ------------------------------------------------------------------ checks
def leaves(out, k):
    def walk(node):
        if 'words' in node:
            yield node['words'], node.get('origins', [1] * k)
        else:
            yield from walk(node['le'])
            yield from walk(node['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


def main():
    res = json.loads(DATA.read_text())
    bad = []
    for row in res['certified']:
        fam = make_family(list(range(row['m'], 0, -1)), row['mask'])
        r = score_output(fam, row['output'])
        au = audit_claim(fam, r['output'], r['certificate']) if r['status'] == 'CERTIFIED' else None
        rep = all(C.is_root(C.run_naive(C.refine(fam['unit_base'], o), w)) and
                  C.is_root(C.run(C.refine(fam['unit_base'], o), w))
                  for ws, o in leaves(row['output'], 2) for w in ws)
        der = None
        if row.get('word_S_params'):
            der = [word_S(row['m'], row['g'], p[0], p[1], p[2], p[3]) for p in row['word_S_params']] == \
                row['output']['words']
        ok = r['status'] == 'CERTIFIED' and au and au[0] and rep and der is not False
        print('m=%-2d {0,%d} %-28s %s leaves=%s lhs=%s audit=%s replay=%s word_S_rederived=%s' % (
            row['m'], row['g'], row['source'], r['status'], r['n_leaves'], [x['lhs'] for x in r['leaves']], au, rep,
            der))
        if not ok:
            bad.append((row['m'], row['g']))
    dc = res['dual_certificates'][0]
    st = C.base_vector(list(range(9, 0, -1)), 1 | 1 << 4)
    p = C.Profile(st, dc['witness_word'])
    wv = p.base + 3 * p.beta[0]
    print('dual certificate m=9 {0,4}: witness B=%d beta=%s, B+3beta0=%d (stored min %d)' % (p.base, p.beta, wv,
                                                                                            dc['min_over_all_words']))
    if wv != dc['min_over_all_words']:
        bad.append('witness')
    if '--tables' in sys.argv:
        sys.path.insert(0, str(HERE / 'reversal_midband_search'))
        import mb
        cost, word, nodes = mb.astar(st, [0, 1], 1, [3, 0])
        T = C.budget(9, 2)
        print('exact oracle: min B + 3 beta_0 = %d over all reduced words (%d nodes); needed >= %d: %s' % (
            cost, nodes, T + 1 + 3 * 7, cost >= T + 1 + 21))
        if cost != dc['min_over_all_words'] or cost < T + 1 + 21:
            bad.append('oracle')
        for row in res['exact_distances']:
            if row['m'] == 9:
                d = mb.tab(9, sum(row['origin'])).d(mb.state_0g(9, row['g'], tuple(row['origin'])))
                if d != row['dist']:
                    bad.append(('dist', row['g'], row['origin']))
        print('exact distances m=9 re-read: %s' % ('ok' if not any(isinstance(b, tuple) and b[0] == 'dist'
                                                                   for b in bad) else 'MISMATCH'))
    print('problems:', bad or 'none')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
