"""Reversal m..1 with two zeros (k = 2): closed-form word_G for masks {0,g}, and re-verification of search outputs.

Offline (no provider calls, no tables, no LLM-generated code). The searches are the scripts in reversal_k2_search/
(run 2026-09-26, raw results copied there unchanged). This script does not search.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py --build   # writes reversal-k2-words.json,
                                                                                   # refuses to overwrite
    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_k2.py           # re-checks the stored JSON,
                                                                                   # writes nothing

--build:
  1. word_G(m, g), a pure stdlib function of (m, g) below, for every (m, g) with m = 9..40 where it is defined:
     bound3_evaluator.score_output, bound3_audit.audit_claim, literal replay (run_naive and run); m = 41..80: replay,
     lrx_m.Profile and lrx_m.mixture_criterion (criterion (7)) with weight 1 only;
  2. every CERTIFIED search output (root surveys m = 11, 12, outer masks m = 13, tree searches): score_output,
     audit_claim, replay of every leaf word on its refined base; misses are stored with their root numbers.
Default (check): re-scores, re-audits and replays every stored CERTIFIED row from its stored words, re-derives
word_G and compares it letter by letter with the stored word. It never recomputes a search.
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
OUT = HERE / 'reversal-k2-words.json'
SEARCH = HERE / 'reversal_k2_search'
sys.path.insert(0, str(HERE))
from reversal_orbit import core_word  # noqa: E402  (verbatim insertion-core generator, REVERSAL-ORBIT.md s.2)

# ---------------------------------------------------------------- closed form for (m..1){0,g}
# Per m mod 4, an ordered rule list. j = m // 4, r = m - g. Parameters (dt, s1, dk, d1, ds2, d2):
#   cut t = (m-3)//4 + dt; core 1 seeded at cell s1 (mod n), k1 = m//2 + dk sweeps, first side d1;
#   core 2 seeded at the middle of the complement arc + ds2, grown until sorted, first side d2; final R walk.
RULES = {
    0: [('g', lambda g, j: g == 1, (-1, 1, -1, 'r', -1, 'r')),
        ('g', lambda g, j: 2 <= g <= j - 1, (0, 0, -1, 'r', -1, 'r')),
        ('g', lambda g, j: g == j and j >= 4, (-2, 2, -2, 'l', 0, 'l')),
        ('r', lambda r, j: 1 <= r <= j - 2, (-1, 0, -1, 'r', -1, 'r')),
        ('r', lambda r, j: r == j - 1, (0, 0, -1, 'l', -1, 'r')),
        ('r', lambda r, j: r == j, (1, -1, -1, 'l', -1, 'r'))],
    1: [('g', lambda g, j: g == 1, (0, 1, 0, 'l', -1, 'r')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, 0, 'l', -1, 'r')),
        ('g', lambda g, j: g == j, (-1, 1, -1, 'r', 0, 'l')),
        ('r', lambda r, j: 0 <= r <= j - 1, (0, 0, 0, 'l', -1, 'r')),
        ('r', lambda r, j: r == j, (1, -1, 0, 'r', -1, 'r'))],
    2: [('g', lambda g, j: g == 1 or g == j, (0, 1, -1, 'l', 0, 'l')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, -1, 'r', 0, 'l')),
        ('r', lambda r, j: 1 <= r <= j - 1, (0, 0, -1, 'r', 0, 'l')),
        ('r', lambda r, j: r == j, (1, -1, -1, 'r', 0, 'l'))],
    3: [('g', lambda g, j: g == 1, (0, 1, 0, 'l', 0, 'l')),
        ('g', lambda g, j: 2 <= g <= j - 1, (1, 0, 0, 'l', 0, 'l')),
        ('g', lambda g, j: g == j, (-2, 1, 0, 'r', 0, 'r')),
        ('r', lambda r, j: 0 <= r <= j, (0, 0, 0, 'l', 0, 'l')),
        ('r', lambda r, j: r == j + 1 and j >= 3, (1, -2, -1, 'r', -1, 'r'))],
}
RULES_TEXT = {
    0: ['g=1: (-1,1,-1,r,-1,r)', '2<=g<=j-1: (0,0,-1,r,-1,r)', 'g=j, j>=4: (-2,2,-2,l,0,l)',
        '1<=r<=j-2: (-1,0,-1,r,-1,r)', 'r=j-1: (0,0,-1,l,-1,r)', 'r=j: (1,-1,-1,l,-1,r)'],
    1: ['g=1: (0,1,0,l,-1,r)', '2<=g<=j-1: (1,0,0,l,-1,r)', 'g=j: (-1,1,-1,r,0,l)', '0<=r<=j-1: (0,0,0,l,-1,r)',
        'r=j: (1,-1,0,r,-1,r)'],
    2: ['g=1 or g=j: (0,1,-1,l,0,l)', '2<=g<=j-1: (1,0,-1,r,0,l)', '1<=r<=j-1: (0,0,-1,r,0,l)',
        'r=j: (1,-1,-1,r,0,l)'],
    3: ['g=1: (0,1,0,l,0,l)', '2<=g<=j-1: (1,0,0,l,0,l)', 'g=j: (-2,1,0,r,0,r)', '0<=r<=j: (0,0,0,l,0,l)',
        'r=j+1, j>=3: (1,-2,-1,r,-1,r)'],
}


def params_G(m, g):
    j, r = m // 4, m - g
    for var, cond, p in RULES[m % 4]:
        if cond(g if var == 'g' else r, j):
            return p
    return None


def word_G(m, g):
    """Single two-core word for (m..1){0,g}, i.e. state (0, m, ..., m-g+1, 0, m-g, ..., 1); None outside the rules."""
    p = params_G(m, g)
    if p is None:
        return None
    dt, s1, dk, d1, ds2, d2 = p
    n = m + 2
    t, k1 = (m - 3) // 4 + dt, m // 2 + dk
    nr = (k1 + 1) // 2 if d1 == 'r' else k1 // 2  # right-growth steps of core 1
    mid = s1 + nr + 1 + (n - k1 - 1) // 2          # middle of the complement arc
    st = C.base_vector(list(range(m, 0, -1)), 1 | 1 << g)
    return core_word(st, t, [(s1 % n, k1, d1), ((mid + ds2) % n, None, d2)], 'R')


# ---------------------------------------------------------------- checks
def leaves_of(out, k):
    def walk(node):
        if 'words' in node:
            yield node['words'], node.get('origins', [1] * k), node.get('picks', [0] * k)
        else:
            yield from walk(node['le'])
            yield from walk(node['ge'])
    return list(walk(out['tree'] if 'tree' in out else out))


def replay_ok(fam, out):
    for words, o, _ in leaves_of(out, fam['k']):
        st = C.refine(fam['unit_base'], o)
        for w in words:
            if not (C.is_root(C.run_naive(st, w)) and C.is_root(C.run(st, w))):
                return False
    return True


def verify(fam, out):
    r = score_output(fam, out)
    row = {'family': fam['id'], 'm': fam['m'], 'k': fam['k'], 'mask': fam['mask'], 'gaps': fam['gaps'],
           'T': fam['budget_unit'], 's': fam['slope_bound'], 'status': r['status'], 'gap': r['gap'],
           'n_leaves': r.get('n_leaves'), 'replay_ok': replay_ok(fam, out), 'output': out}
    if r.get('leaves'):
        row['leaves'] = [{'box': x['box'], 'origins': x['origins'], 'picks': x['picks'], 'lhs': x['lhs'],
                          'support': [[s['weight'], s['base'], s['beta'], len(s['word'])] for s in x['support']]}
                         for x in r['leaves']]
    if r['status'] == 'CERTIFIED':
        row['audit'] = list(audit_claim(fam, r['output'], r['certificate']))
    return row


def fam_of(m, mask, labels=None):
    return make_family(labels or list(range(m, 0, -1)), mask)


def ok_row(row):
    return row['status'] == 'CERTIFIED' and row['replay_ok'] and row.get('audit', [False])[0] is True


def build():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    t0 = time.time()
    res = {'schema': 'lrx-reversal-k2-v1', 'date': '2026-09-26',
           'semantics': 'words sort the (refined) base to (1..m,0..0); L: (v1..vn)->(v2..vn,v1), R = L^-1, X swaps '
                        'v1,v2 (lrx_m.run_naive); every stored word replayed with run_naive and run',
           'conditionality': "certificates are conditional on the research group's Lemma 1 (with refinement) and "
                             'criteria (7)/(8) with m as a parameter, as implemented by bound3_evaluator; each '
                             'CERTIFIED row was re-audited by bound3_audit.audit_claim',
           'generator': 'word_G(m, g) in checks/reversal_k2.py; core_word from checks/reversal_orbit.py',
           'rules': {str(k): v for k, v in RULES_TEXT.items()},
           'search_scripts': 'reversal_k2_search/ (scan0g.py, fitscan.py, fitscan2.py, scan2.py, k2gen.py, cand.py, '
                             'candlp.py, survey_root.py, trees.py)',
           'formula_G': [], 'formula_G_failures': [], 'formula_G_replay_41_80': {}, 'stored': [], 'not_found': []}
    # 1. word_G
    for m in range(9, 41):
        for g in range(1, m + 1):
            w = word_G(m, g)
            if w is None:
                continue
            fam = fam_of(m, 1 | 1 << g)
            row = verify(fam, {'words': [w]})
            row.update(tag='word_G', g=g, params=list(params_G(m, g)), length=len(w),
                       length_minus_T=len(w) - fam['budget_unit'])
            res['formula_G'].append(row)
            if not ok_row(row):
                res['formula_G_failures'].append([m, g])
        print('word_G m=%d rows=%d failures so far %d' % (m, sum(1 for x in res['formula_G'] if x['m'] == m),
                                                          len(res['formula_G_failures'])), flush=True)
    for m in range(41, 81):
        cnt, bad = 0, []
        for g in range(1, m + 1):
            w = word_G(m, g)
            if w is None:
                continue
            cnt += 1
            fam = fam_of(m, 1 | 1 << g)
            p = C.Profile(fam['unit_base'], w)
            ok7 = C.mixture_criterion([(p.base, p.beta)], [1], 2, m=m)[0]
            if not (ok7 and replay_ok(fam, {'words': [w]})):
                bad.append(g)
        res['formula_G_replay_41_80'][m] = {'words': cnt, 'failures': bad}
        print('word_G replay m=%d words=%d failures=%s' % (m, cnt, bad), flush=True)
    # 2. search outputs
    seen = set()
    for name in ('survey-m11.jsonl', 'survey-m12.jsonl', 'survey-m13-outer.jsonl', 'trees-a.jsonl', 'trees-b.jsonl'):
        for x in (json.loads(s) for s in (SEARCH / name).read_text().splitlines() if s.strip()):
            fam = fam_of(x['m'], x['mask'], x.get('labels'))
            if 'output' not in x or x.get('status') == 'NOT_FOUND':
                res['not_found'].append({'family': fam['id'], 'm': fam['m'], 'gaps': fam['gaps'], 'source': name,
                                         'root_minB_minus_T': x.get('root_minB_minus_T'),
                                         'root_slope_excess': x.get('root_slope_excess'),
                                         'origins_tried': x.get('origins_tried'), 'maxdepth': x.get('maxdepth'),
                                         'tmax': x.get('tmax')})
                continue
            if fam['id'] in seen:
                continue
            seen.add(fam['id'])
            row = verify(fam, x['output'])
            row.update(source=name)
            res['stored'].append(row)
            print('%-24s m=%d %-40s %s leaves=%s audit=%s replay=%s' % (name, fam['m'], fam['id'][4:], row['status'],
                  row['n_leaves'], row.get('audit'), row['replay_ok']), flush=True)
    res['stored_failures'] = [x['family'] for x in res['stored'] if not ok_row(x)]
    res['seconds'] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print('word_G rows', len(res['formula_G']), 'failures', res['formula_G_failures'])
    print('stored', len(res['stored']), 'failures', res['stored_failures'], 'not_found', len(res['not_found']))
    print('wrote', OUT.relative_to(HERE.parents[2]), res['seconds'], 's')


def check():
    if not OUT.exists():
        sys.exit('%s not found; run with --build first' % OUT)
    t0 = time.time()
    d = json.loads(OUT.read_text())
    bad = []
    for row in d['formula_G']:
        w = word_G(row['m'], row['g'])
        if w != row['output']['words'][0]:
            bad.append(('word_G differs', row['m'], row['g']))
    for row in d['formula_G'] + d['stored']:
        fam = fam_of(row['m'], row['mask'], [int(x) for x in row['family'].split('-labels')[1].split('.')]
                     if '.' in row['family'].split('-labels')[1] else [int(c) for c in row['family'].split('-labels')[1]])
        if fam['id'] != row['family']:
            bad.append(('family id', row['family']))
            continue
        again = verify(fam, row['output'])
        if not ok_row(again) or again['status'] != row['status'] or again['gap'] != row['gap']:
            bad.append(('re-verify', row['family']))
    print('re-checked %d word_G rows and %d stored rows in %.1f s; problems: %s'
          % (len(d['formula_G']), len(d['stored']), time.time() - t0, bad or 'none'))
    return not bad


if __name__ == '__main__':
    if '--build' in sys.argv[1:]:
        build()
    else:
        sys.exit(0 if check() else 1)
