"""Reversal m..1 with three zeros (k = 3): survey certificates at m = 9..11 and the closed form word_W on the corner
sub-band {0, g1, g2}. Re-check only: this script never searches.

Offline (no provider calls, no tables, no LLM-generated code). The searches are the scripts in reversal_k3_search/
(run 2026-09-26, raw results kept there unchanged).

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k3.py --build   # writes reversal-k3-words.json
                                                                                   # from the search outputs; refuses
                                                                                   # to overwrite
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k3.py           # re-checks the stored JSON,
                                                                                   # writes nothing

Both modes, for every stored CERTIFIED output: bound3_evaluator.score_output must return CERTIFIED,
bound3_audit.audit_claim must return (True, 'ok'), every leaf word must sort its refined base under lrx_m.run_naive
and lrx_m.run, and every word is re-derived letter by letter from its stored generator parameters (core_word3).
Closed form word_W(m, g1, g2) on its band: m = 9..24 score_output + audit_claim + replay; m = 25..40 replay +
lrx_m.Profile + lrx_m.mixture_criterion (criterion (7)) with weight 1.
"""
import json
import sys
import time
from pathlib import Path

from integrations import lrx_m as C
from integrations.bound3_audit import audit_claim
from integrations.bound3_evaluator import score_output
from integrations.bound_task import make_family

HERE = Path(__file__).resolve().parent
OUT = HERE / 'reversal-k3-words.json'
SEARCH = HERE / 'reversal_k3_search'


# ---------------------------------------------------------------- generator (stdlib, plain)
def core_word3(state, cores, fin, zfree=False):
    """Insertion-core word (REVERSAL-ORBIT.md s.2, core_word) with one cut per core and up to three cores.
    Physical model of lrx_m: cells 0..n-1, cursor c = 0, L: c+1, R: c-1, X swaps cells c, c+1.
    cores: [(seed, sweeps | None, first side 'r'|'l', cut t)]; core i sorts into the order t+1..m, zeros, 1..t
    (zeros tied, never swapped with each other). A core with sweeps None grows until the cycle is sorted.
    'r' inserts cell hi+1 by carrying it left past the core cells of larger rank (X (RX)^(s-1)); 'l' inserts cell
    lo-1 by carrying it right past those of smaller rank (X (LX)^(s-1)). The cursor moves between steps by the
    shorter way round (L on ties). Sides alternate; with zfree, absorbing a zero cell keeps the side.
    Then a walk fin ('R' or 'L') to label 1. Returns None if the cycle is not sorted."""
    n = len(state)
    m = sum(1 for x in state if x)
    cell, w, c = list(state), [], 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    def srt():
        i = cell.index(1)
        return [cell[(i + x) % n] for x in range(m)] == list(range(1, m + 1))

    for seed, sweeps, side, t in cores:
        rk = {x: i for i, x in enumerate(list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1)))}
        lo = hi = seed
        ln, cnt = 1, 0
        while ln < n and (not srt() if sweeps is None else cnt < sweeps):
            if side == 'r':
                j = (hi + 1) % n
                v = cell[j]
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[v]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                v = cell[j]
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[v]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
            cnt += 1
            if not (zfree and v == 0):
                side = 'l' if side == 'r' else 'r'
    if not srt():
        return None
    p = cell.index(1)
    w.append('L' * ((p - c) % n) if fin == 'L' else 'R' * ((c - p) % n))
    return ''.join(w)


# ---------------------------------------------------------------- closed form word_W on the corner band
# Per m mod 4: (dt, dk, d1, d2). Cut t = (m-3)//4 + dt; core 1 seeded at cell 0 (the gap-0 zero) with m//2 + dk
# sweeps, first side d1; core 2 seeded at the middle of the complement arc, grown until sorted, first side d2;
# final R walk. n = m + 3.
PARAMS_W = {0: (0, 1, 'l', 'r'), 1: (0, 0, 'r', 'l'), 2: (1, 0, 'l', 'l'), 3: (-1, 1, 'r', 'r')}
# Band, j = m//4, r2 = m - g2: (g1 range, r2 range) per m mod 4.
BAND_TEXT = {0: '2 <= g1 <= j-1, 0 <= r2 <= j-1', 1: '3 <= g1 <= j-1, 0 <= r2 <= j-1',
             2: '2 <= g1 <= j-1, 0 <= r2 <= j', 3: '3 <= g1 <= j, 0 <= r2 <= j-1'}


def in_band(m, g1, g2):
    j, r2, q = m // 4, m - g2, m % 4
    lo1, hi1, hi2 = {0: (2, j - 1, j - 1), 1: (3, j - 1, j - 1), 2: (2, j - 1, j), 3: (3, j, j - 1)}[q]
    return lo1 <= g1 <= hi1 and 0 <= r2 <= hi2 and g1 < g2


def band(m):
    return [(g1, g2) for g1 in range(1, m + 1) for g2 in range(g1 + 1, m + 1) if in_band(m, g1, g2)]


def unit_state(m, g1, g2):
    return C.base_vector(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)


def params_W(m):
    dt, dk, d1, d2 = PARAMS_W[m % 4]
    n = m + 3
    t, k1 = (m - 3) // 4 + dt, m // 2 + dk
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2        # right-growth steps of core 1
    mid = nr + 1 + (n - k1 - 1) // 2                    # middle of the complement arc (core 1 seeded at 0)
    return [(0, k1, d1, t), (mid % n, None, d2, t)], 'R'


def word_W(m, g1, g2):
    cores, fin = params_W(m)
    return core_word3(unit_state(m, g1, g2), cores, fin)


# ---------------------------------------------------------------- checks
def leaves_of(out, k=3):
    def walk(node):
        if 'words' in node:
            yield node['words'], node.get('origins', [1] * k)
        else:
            yield from walk(node['le'])
            yield from walk(node['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


def replay_ok(fam, out):
    for words, o in leaves_of(out):
        st = C.refine(fam['unit_base'], o)
        for w in words:
            if not (C.is_root(C.run_naive(st, w)) and C.is_root(C.run(st, w))):
                return False
    return True


def rederive_ok(fam, out, params):
    """params: [[origins, word, [zfree, cores, fin]]]; every leaf word must be re-derived exactly on its refined base."""
    par = {(tuple(o), w): p for o, w, p in params}
    for words, o in leaves_of(out):
        st = C.refine(fam['unit_base'], o)
        for w in words:
            p = par.get((tuple(o), w))
            if p is None:
                return False
            zf, cores, fin = p
            if core_word3(st, [tuple(c) for c in cores], fin, zf) != w:
                return False
    return True


def check_output(m, mask, out, params=None):
    fam = make_family(list(range(m, 0, -1)), mask)
    r = score_output(fam, out)
    au = tuple(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
    rep = replay_ok(fam, out)
    der = rederive_ok(fam, out, params) if params is not None else None
    return r, au, rep, der


def closed_form_rows(m_eval=24, m_top=40):
    """-> rows (m, g1, g2, B - T, beta, how) and failures."""
    rows, bad = [], []
    for m in range(9, m_top + 1):
        T = C.budget(m, 3)
        for g1, g2 in band(m):
            w = word_W(m, g1, g2)
            fam = make_family(list(range(m, 0, -1)), 1 | 1 << g1 | 1 << g2)
            p = C.Profile(fam['unit_base'], w)
            ok7, B, beta = C.mixture_criterion([(p.base, p.beta)], [1], 3, m=m)
            rep = replay_ok(fam, {'words': [w]})
            how = 'replay+criterion7'
            if m <= m_eval:
                r = score_output(fam, {'words': [w]})
                au = tuple(audit_claim(fam, r['output'], r['certificate'])) if r['status'] == 'CERTIFIED' else None
                if r['status'] != 'CERTIFIED' or au != (True, 'ok'):
                    bad.append(('word_W evaluator/audit', m, g1, g2, r['status'], au))
                how = 'evaluator+audit+replay'
            if not ok7 or not rep:
                bad.append(('word_W criterion7/replay', m, g1, g2, ok7, rep))
            rows.append([m, g1, g2, p.base - T, list(p.beta), how])
    return rows, bad


# ---------------------------------------------------------------- build
def load_search():
    rows = []
    for m in (9, 10, 11):
        for line in (SEARCH / ('survey-m%d.jsonl' % m)).read_text().splitlines():
            r = json.loads(line)
            rows.append(('root survey, two-core pool', r))
    extra = {}
    for f in sorted(SEARCH.glob('misses-*.jsonl')):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r['status'] == 'CERTIFIED' and isinstance(r.get('params'), list):  # (origin, word)-keyed params only
                extra[(r['m'], r['mask'])] = (f.name, r)
    return rows, extra


def build():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    t0 = time.time()
    rows, extra = load_search()
    certified, misses, bad = [], [], []
    for src, r in rows:
        m, mask = r['m'], r['mask']
        if r['status'] == 'CERTIFIED':
            params = [[[1, 1, 1], w, s[3]] for w, s in zip(r['output']['words'], r['support'])]
            out, how = r['output'], src
        elif (m, mask) in extra:
            f, e = extra[(m, mask)]
            out, how, params = e['output'], '%s (%s)' % (e['how'], f), e['params']
        else:
            misses.append({'m': m, 'mask': mask, 'gaps': r['gaps'], 'root_minB_minus_T': r['root_minB_minus_T'],
                           'root_slope_excess': r['root_slope_excess'],
                           'binding': 'slope' if r['root_slope_excess'] != '0' else 'base'})
            continue
        res, au, rep, der = check_output(m, mask, out, params)
        ok = res['status'] == 'CERTIFIED' and au == (True, 'ok') and rep and der
        if not ok:
            bad.append((m, mask, res['status'], au, rep, der))
        certified.append({'m': m, 'mask': mask, 'gaps': r['gaps'], 'source': how, 'output': out,
                          'params': params, 'n_leaves': res['n_leaves'], 'lhs': [x['lhs'] for x in res['leaves']],
                          'audit': list(au) if au else None, 'replay': rep, 'rederived': der})
    cf_rows, cf_bad = closed_form_rows()
    bad += cf_bad
    data = {'date': '2026-09-26', 'notes': 'REVERSAL-K3.md; conditional on Lemma 1 and criteria (7)/(8) (group, m=8 '
                                         'manuscript) with m as a parameter',
            'certified': certified, 'misses': misses,
            'closed_form': {'name': 'word_W', 'params_by_m_mod_4': {str(q): list(v) for q, v in PARAMS_W.items()},
                            'band_by_m_mod_4': {str(q): v for q, v in BAND_TEXT.items()}, 'rows': cf_rows,
                            'words_m9_24': {'%d,%d,%d' % (m, a, b): word_W(m, a, b)
                                            for m, a, b, *_ in cf_rows if m <= 24}},
            'problems': [list(map(str, x)) for x in bad]}
    OUT.write_text(json.dumps(data, indent=1))
    summarize(data)
    print('problems:', bad or 'none', 'wall', round(time.time() - t0, 1))
    sys.exit(1 if bad else 0)


def summarize(data):
    by = {}
    for r in data['certified']:
        by.setdefault(r['m'], []).append(r)
    for m in sorted(by):
        n = len(by[m]) + sum(1 for x in data['misses'] if x['m'] == m)
        print('m=%d certified %d / %d (root %d)' % (m, len(by[m]), n,
                                                   sum(1 for r in by[m] if r['source'].startswith('root'))))
    cf = data['closed_form']['rows']
    print('word_W rows: %d by evaluator+audit+replay (m <= 24), %d by replay+criterion (7) (m = 25..40)' % (
        sum(1 for r in cf if r[5].startswith('evaluator')), sum(1 for r in cf if r[5].startswith('replay'))))


def check():
    t0 = time.time()
    data = json.loads(OUT.read_text())
    bad = []
    for row in data['certified']:
        res, au, rep, der = check_output(row['m'], row['mask'], row['output'], row['params'])
        if not (res['status'] == 'CERTIFIED' and au == (True, 'ok') and rep and der):
            bad.append((row['m'], row['mask'], res['status'], au, rep, der))
    cf_rows, cf_bad = closed_form_rows()
    bad += cf_bad
    if [r[:5] for r in cf_rows] != [r[:5] for r in data['closed_form']['rows']]:
        bad.append('closed-form rows differ from the stored ones')
    for key, w in data['closed_form']['words_m9_24'].items():
        m, a, b = map(int, key.split(','))
        if word_W(m, a, b) != w:
            bad.append(('word_W letters differ', key))
    summarize(data)
    print('stored certified rows re-checked: %d; misses stored: %d' % (len(data['certified']), len(data['misses'])))
    print('problems:', bad or 'none', 'wall', round(time.time() - t0, 1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    build() if '--build' in sys.argv else check()
