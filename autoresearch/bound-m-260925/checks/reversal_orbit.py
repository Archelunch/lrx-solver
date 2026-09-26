"""Reversal orbit beyond (m..1){0,m}: insertion-core words, re-verification of every stored certificate.

Offline (no provider calls, no tables, no LLM-generated code). The search that produced the stored outputs is the
set of scripts in reversal_orbit_search/ (run 2026-09-26; results copied there unchanged). This script does not
search. It
  1. re-scores every stored CERTIFIED output with bound3_evaluator.score_output, re-audits it with the independent
     bound3_audit.audit_claim, and replays every leaf word literally (lrx_m.run_naive and run) on its refined base;
  2. builds the closed-form single word word_R1(m) for the family (m..1){1,m} (mask 2 | 1<<m) and scores and audits
     it at m = 9..40, replay and criterion (7) only at m = 41..200;
  3. re-checks the hand-derived closed forms for word_C (reversal_m13.py) at m = 5..60, 1 <= a <= m-2.
Writes reversal-orbit-words.json next to this file and refuses to overwrite.

    PYTHONPATH=. python autoresearch/bound-m-260925/checks/reversal_orbit.py
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
OUT = HERE / 'reversal-orbit-words.json'
SEARCH = HERE / 'reversal_orbit_search'
sys.path.insert(0, str(HERE))
from reversal_m13 import word_C  # noqa: E402


# ---------------------------------------------------------------- generator (pure stdlib function of the state)
def core_word(state, t, cores, fin):
    """Insertion-core word. Physical model of lrx_m: cells 0..n-1 on a cycle, cursor c = 0, L: c+1, R: c-1,
    X swaps cells c, c+1. Target order: cut t, i.e. labels t+1..m, zeros (tied), labels 1..t.
    A core is a cyclic arc grown from one seed cell; sides alternate starting with `side`. Growing on the right
    inserts cell hi+1 into the sorted core by carrying it leftwards (X (RX)^(s-1)) past the s core elements of
    larger rank; growing on the left inserts cell lo-1 rightwards (X (LX)^(s-1)). Zeros never swap with zeros.
    cores: [(seed, sweeps or None = until the cycle is sorted, side)]. Then a walk to label 1 ('R' or 'L').
    Returns the word, or None if the cycle is not cyclically sorted after the cores. word_C(m, a) grows its cores
    the same way but always carries across the whole core; it is not claimed to be a special case of this."""
    n = len(state)
    m = sum(1 for x in state if x)
    order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
    rk = {x: i for i, x in enumerate(order)}
    cell, w, c = list(state), [], 0

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    def srt():
        i = cell.index(1)
        return [cell[(i + x) % n] for x in range(m)] == list(range(1, m + 1))

    for seed, sweeps, side in cores:
        lo = hi = seed
        ln, cnt = 1, 0
        while ln < n and (not srt() if sweeps is None else cnt < sweeps):
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
            cnt += 1
            side = 'l' if side == 'r' else 'r'
    if not srt():
        return None
    p = cell.index(1)
    w.append('L' * ((p - c) % n) if fin == 'L' else 'R' * ((c - p) % n))
    return ''.join(w)


def word_R1(m):
    """Family (m..1){1,m}: state (m, 0, m-1, ..., 1, 0). One word: cut (m-3)//4; core 1 from cell 0, m//2 sweeps,
    first 'l'; core 2 from cell m//2+1 until sorted, first 'r' iff m = 1 mod 4; final R walk."""
    st = C.base_vector(list(range(m, 0, -1)), 2 | 1 << m)
    return core_word(st, (m - 3) // 4, [(0, m // 2, 'l'), (m // 2 + 1, None, 'r' if m % 4 == 1 else 'l')], 'R')


def word_C_length(m, a):
    """Hand count (REVERSAL-ORBIT.md section 4), valid for 1 <= a <= m-2."""
    r = m - a
    w0 = r // 2 + 1 if r % 2 == 0 else ((r + 3) // 2 if a % 2 else (r + 1) // 2)
    return (a * a + 3 * a - 1) + ((r - 1) ** 2 + r - 2) + w0 + a // 2


# ---------------------------------------------------------------- checks
def leaves_of(out, k):
    """Raw output -> [(words, origins, picks)] in tree order (no boxes; the evaluator derives those)."""
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


def main():
    if OUT.exists():
        sys.exit('refusing to overwrite %s' % OUT)
    t0 = time.time()
    res = {'schema': 'lrx-reversal-orbit-v1', 'date': '2026-09-26',
           'semantics': 'words sort the (refined) base to (1..m,0..0); L: (v1..vn)->(v2..vn,v1), R = L^-1, X swaps '
                        'v1,v2 (lrx_m.run_naive); every stored word replayed with run_naive and run',
           'conditionality': "certificates are conditional on the research group's Lemma 1 (with refinement) and "
                             'criteria (7)/(8) with m as a parameter, as implemented by bound3_evaluator; each '
                             'CERTIFIED row was re-audited by bound3_audit.audit_claim',
           'search_scripts': 'reversal_orbit_search/ (gen.py, fast.py, engine.py, survey.py, regen.py, local.py, '
                             'formula.py, params.py)', 'stored': [], 'not_found': [], 'formula_R1': {}}
    # 1. stored search outputs
    seen = set()
    k2 = json.loads((SEARCH / 'k2-m9-10-results.json').read_text())
    regen = [json.loads(x) for x in (SEARCH / 'regen-results.jsonl').read_text().splitlines() if x.strip()]
    for src, rows in (('k2-m9-10', k2), ('regen', regen)):
        for x in rows:
            labels = x.get('labels') or list(range(x['m'], 0, -1))  # the k=2 survey used labels m..1 only
            fam = make_family(labels, x['mask'])
            tag = x.get('tag', 'rev_k2')
            if x['status'] != 'CERTIFIED':
                res['not_found'].append({'family': fam['id'], 'm': fam['m'], 'gaps': fam['gaps'], 'tag': tag,
                                         'source': src, 'root_minB_minus_T': x.get('root_minB_minus_T'),
                                         'root_slope_excess': x.get('root_slope_excess')})
                continue
            if fam['id'] in seen:
                continue
            seen.add(fam['id'])
            row = verify(fam, x['output'])
            row.update(tag=tag, source=src)
            res['stored'].append(row)
            print('%-9s m=%d %-44s %s leaves=%s audit=%s replay=%s' % (src, fam['m'], fam['id'][4:], row['status'],
                  row['n_leaves'], row.get('audit'), row['replay_ok']), flush=True)
    # 2. closed-form word for (m..1){1,m}
    fails = []
    for m in range(9, 201):
        fam = make_family(list(range(m, 0, -1)), 2 | 1 << m)
        w = word_R1(m)
        p = C.Profile(fam['unit_base'], w)
        ok7 = C.mixture_criterion([(p.base, p.beta)], [1], 2, m=m)[0]
        row = {'length': len(w), 'length_minus_T': len(w) - fam['budget_unit'], 'beta': p.beta,
               'replay_ok': replay_ok(fam, {'words': [w]}), 'criterion7': ok7}
        if m <= 40:
            v = verify(fam, {'words': [w]})
            row.update(status=v['status'], lhs=v['leaves'][0]['lhs'], audit=v.get('audit'), word=w)
            print('R1 m=%d len-T=%d beta=%s %s audit=%s' % (m, row['length_minus_T'], p.beta, v['status'],
                                                            v.get('audit')), flush=True)
        if not (row['replay_ok'] and ok7 and row.get('status', 'CERTIFIED') == 'CERTIFIED'
                and row.get('audit', [True])[0]):
            fails.append(m)
        res['formula_R1'][m] = row
    res['formula_R1_failures_m9_200'] = fails
    print('R1 failures m=9..200:', fails)
    # 3. word_C closed forms
    bad_len, bad_beta = [], []
    for m in range(5, 61):
        u = [0] + list(range(m, 0, -1)) + [0]
        for a in range(1, m - 1):
            w = word_C(m, a)
            p = C.Profile(u, w)
            T = C.budget(m, 2)
            if len(w) != word_C_length(m, a) or 2 * (len(w) - T) != (2 * a - m + 2) ** 2 - 2 - (m % 2):
                bad_len.append([m, a])
            if p.base != len(w) or p.beta != [2 * a + 1, 2 * a]:
                bad_beta.append([m, a, p.beta])
    res['word_C_closed_forms_m5_60'] = {
        'length': 'len = (a^2+3a-1) + ((r-1)^2+r-2) + W0 + floor(a/2), r = m-a, W0 = r/2+1 (r even), (r+3)/2 '
                  '(a, r odd), (r+1)/2 (a even, r odd); equivalently len - T = 2(a-(m-2)/2)^2 - 1 - (m mod 2)/2',
        'length_failures': bad_len, 'beta_(2a+1,2a)_failures': bad_beta}
    print('word_C length failures', len(bad_len), 'beta failures', bad_beta)
    res['seconds'] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print('wrote', OUT.relative_to(HERE.parents[2]), res['seconds'], 's')


if __name__ == '__main__':
    main()
