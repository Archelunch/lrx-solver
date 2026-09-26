#!/usr/bin/env python3
"""Print a compact trace of fast_colgen.py logs: python3 summarize.py runs/colgen-*.log"""
import json, sys
for f in sys.argv[1:]:
    print('==', f)
    for l in open(f):
        if l.startswith('  oracle'):
            d = json.loads(l[9:])
            ws = d.get('wstats') or []
            print('   W=%s K=%d start=%s build=%ss -> %s F=%s B=%s beta=%s | weighted exp %s | exact exp %s s %s'
                  % (d['W'], d['K'], d['start_bound'], d['tables'][0].get('build_s') if d['tables'] else None,
                     d['result'], d.get('F'), d.get('B'), d.get('beta'), [w.get('expanded') for w in ws],
                     (d.get('stats') or {}).get('expanded'), (d.get('stats') or {}).get('search_s')))
        elif l.startswith(('iter', 'verdict', 'wrote', 'Traceback')):
            print(' ', l.strip()[:170])
