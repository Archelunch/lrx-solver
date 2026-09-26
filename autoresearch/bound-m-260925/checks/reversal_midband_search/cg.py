"""Exact leaf LP over all words: python cg.py m g o0 o1 [bounded-width-axis0 or -1]"""
import time, sys, json
from mb import *
sys.path.insert(0, str(ROOT/'autoresearch/bound-m-260925/checks/reversal_orbit_search'))
from fast import gen_pool
m, g, o0, o1 = map(int, sys.argv[1:5])
wid = int(sys.argv[5]) if len(sys.argv) > 5 else -1
o=(o0,o1); st = state_0g(m,g,o); picks=[0,o0]
tb = tab(m, o0+o1); T = C.budget(m, o0+o1); s = m-2
t0 = time.process_time()
d0,total,words,_ = shortest_dag(st, tb, limit=300)
pool = list(gen_pool(st)) + words
res = column_generation(st, picks, s, T, {} if wid < 0 else {0: wid}, tb, pool, log=lambda *a: print(*a, flush=True), maxnodes=int(__import__("os").environ.get("MAXN","12000000")))
items = sorted(res['pool'])
row = {'m': m, 'g': g, 'origin': list(o), 'picks': [0, 0], 'width0': wid, 'dist': d0, 'T': T, 'n_shortest': total,
       'value_pool': str(res['value_pool']), 'lower_bound': None if res['lower_bound'] is None else str(res['lower_bound']), 'lam': res['lam'],
       'exact': res['lower_bound'] is not None and res['lower_bound'] >= res['value_pool'], 'nodes': res['nodes'], 'cpu': round(time.process_time()-t0, 1),
       'front': [[x[0], list(x[1:]), res['pool'][x]] for x in items]}
print('RESULT', m, g, o, 'wid', wid, 'd', d0, 'T', T, 'value', row['value_pool'], 'LB', row['lower_bound'], 'lam', res['lam'], 'cpu', row['cpu'], flush=True)
with open('cg-results.jsonl', 'a') as f:
    f.write(json.dumps(row) + '\n')
