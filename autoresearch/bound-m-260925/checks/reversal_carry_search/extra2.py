"""canon2 (v2 family) root LP for band values not certified by word_M or canon v1; appends to a jsonl."""
import sys, json, time
from common import *
from canon2 import front2
from integrations.lift_evaluator import mixture_lp
sys.path.insert(0, str(ROOT / 'autoresearch/bound-m-260925/checks'))
import reversal_carry as RC
done = set()
for l in open('canon-root-14-24.jsonl'):
    r = json.loads(l)
    if r['status'] == 'CERTIFIED': done.add((r['m'], r['g']))
out = open(sys.argv[3], 'a')
for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
    cf = RC.closed_form_rows(m)
    cov = {g for side in cf for g, _, _ in cf[side]}
    cand = [g for g in RC.band(m) if g not in cov and (m, g) not in done]
    # only the values next to the covered ends, plus g = floor(m/2) for the binding-constraint diagnostic
    lo_end = max([g for g in RC.band(m) if (g in cov or (m, g) in done) and g < m / 2] or [m // 4])
    hi_end = min([g for g in RC.band(m) if (g in cov or (m, g) in done) and g > m / 2] or [m - m // 4])
    for g in sorted({lo_end + 1, hi_end - 1} & set(cand)):
        t0 = time.process_time()
        fr = front2(m, g); keys = list(fr)
        r = root_lp(m, keys); T = C.budget(m, 2)
        w, B, _, t = mixture_lp([(k[0], list(k[1:])) for k in keys], 2, m - 2)
        sup = [(keys[i][0] - T, keys[i][1:], fr[keys[i]][1], str(x)) for i, x in enumerate(r['weights']) if x]
        row = {'m': m, 'g': g, 'status': r['status'], 'lhs': str(r.get('value')), 'gap': str(r['gap']),
               'min_base_excess_slopes_feasible': str(B - T) if t == 0 else None, 'min_uniform_slope_excess': str(t),
               'support': [[x[0], list(x[1]), list(x[2]), x[3]] for x in sup],
               'words': [fr[keys[i]][0] for i, x in enumerate(r['weights']) if x], 'cpu': round(time.process_time() - t0, 1)}
        out.write(json.dumps(row) + '\n'); out.flush()
        print(m, g, r['status'], r.get('value'), r['gap'], 'minB-T', row['min_base_excess_slopes_feasible'], 't', t,
              '%.0fs' % row['cpu'], flush=True)
