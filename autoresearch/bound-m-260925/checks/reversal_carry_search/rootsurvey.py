import sys, time, json
from common import *
import pools
out = open(sys.argv[3], 'a') if len(sys.argv) > 3 else None
for m in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
    for g in range(m // 4 + 1, m - m // 4):
        t0 = time.process_time()
        P = pools.pool(m, g, (1, 1))
        fr = P[(0, 1)]; keys = list(fr)
        r = root_lp(m, keys)
        T = C.budget(m, 2)
        sup = [(keys[i][0] - T, keys[i][1:], fr[keys[i]][1], str(x)) for i, x in enumerate(r['weights']) if x]
        cpu = time.process_time() - t0
        print(m, g, r['status'], r.get('value'), r['gap'], '%.1fs' % cpu, flush=True)
        for x in sup: print('    ', x)
        if out:
            out.write(json.dumps({'m': m, 'g': g, 'status': r['status'], 'lhs': str(r.get('value')), 'gap': str(r['gap']),
                                  'support': [[x[0], list(x[1]), list(x[2]), x[3]] for x in sup],
                                  'words': [fr[keys[i]][0] for i, x in enumerate(r['weights']) if x],
                                  'cpu': round(cpu, 1)}) + '\n'); out.flush()
