#!/usr/bin/env python3
"""lrxtree_wide vs lrxtree on every n <= 16 instance type of runs/ (identical arguments): same table statistics,
start bound, weighted and exact expansion / stored counts, RESULT line and word; where the historical run was
complete, the stored expansion count as well.  Historical runs that stopped at the memory cap are re-run with a
node cap (--cap), so both binaries stop at the same expansion and must report the same interrupted bucket.

    python3 crosscheck_wide.py [--only NAME] [--mem GB]
"""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import treeoracle_wide as TW
import treeoracle as TO
NG = TO.NG

C9 = [[[9, 8], [7, 6], [5, 4], [3, 2, 1]]]
C11a = [[11, 10, 9], [8, 7, 6], [5, 4, 3], [2, 1]]
C11b = [[11, 10, 9, 8], [7, 6, 5, 4], [3, 2, 1]]
C12a = [[12, 11, 10], [9, 8, 7], [6, 5, 4], [3, 2, 1]]
C12b = [[12, 11, 10, 9], [8, 7, 6, 5], [4, 3, 2, 1]]
# name, m, g, origin, picks(in-block), W, K, classes, omega, wcap, cap, stored exact expansions (complete runs;
# (count, table vectors) for the three runs made before the weight-0 zero merge of lrxtree.c)
CASES = [
    ('m9-o11-W100', 9, 4, (1, 1), (0, 0), (1, 0, 0), 53, C9, [], None, None, (36321, 831600)),
    ('m9-o21-W100', 9, 4, (2, 1), (0, 0), (1, 0, 0), 60, C9, [], None, None, (156186, 9979200)),
    ('m9-o21-W1.16.0', 9, 4, (2, 1), (0, 0), (1, 16, 0), 172, C9, [], None, None, 1166922),
    ('m9-o21-W13.36.0', 9, 4, (2, 1), (0, 0), (13, 36, 0), 1032, C9, [], None, None, 279709),
    ('m9-o21-W9.14.0', 9, 4, (2, 1), (0, 0), (9, 14, 0), 638, C9, [], None, None, 159397),
    ('m11g5-o11-W100', 11, 5, (1, 1), (0, 0), (1, 0, 0), 76, [C11a], [], None, None, 3977616),
    ('m11g5-o21-p00-refute', 11, 5, (2, 1), (0, 0), (1, 2, 0), 103, [C11a], [], None, None, 52824541),
    ('m11g5-o21-p10-refute', 11, 5, (2, 1), (1, 0), (1, 2, 0), 103, [C11a], ['3/2'], 20000000, None, 52487139),
    ('m11g5-o21-W3.7.0', 11, 5, (2, 1), (0, 0), (3, 7, 0), 318, [C11a], ['3/2'], 20000000, None, 61326354),
    ('m11g5-o31-weighted-found', 11, 5, (3, 1), (0, 0), (1, 1, 0), 103, [C11b], ['5/4'], 40000000, None, None),
    ('m11g5-o31-capped', 11, 5, (3, 1), (0, 0), (1, 1, 0), 103, [C11b], ['3/2'], 20000000, 40000000, None),
    ('m12g5-o11-W100', 12, 5, (1, 1), (0, 0), (1, 0, 0), 89, [C12a], [], None, None, (52484393, 67267200)),
    ('m12g6-o11-W100', 12, 6, (1, 1), (0, 0), (1, 0, 0), 89, [C12a], [], None, None, 43440609),
    ('m12g5-o21-capped', 12, 5, (2, 1), (0, 0), (1, 2, 0), 119, [C12b], [], None, 40000000, None),
    ('m12g5-o31-capped', 12, 5, (3, 1), (0, 0), (1, 1, 0), 119, [C12b], ['5/4', '2/1'], 10000000, 10000000, None),
    ('m12g6-o31-point-capped', 12, 6, (3, 1), (0, 0), (1, 0, 0), 109, [C12b], [], None, 40000000, None),
    ('m12g6-o21-point3-capped', 12, 6, (2, 1), (0, 0), (1, 1, 0), 109, [C12b], ['3/2'], 20000000, 40000000, None),
]


def norm(cls):
    return cls if isinstance(cls[0][0], list) else [cls]


def summary(r):
    return {'result': r.get('result'), 'F': r.get('F'), 'word': r.get('word'), 'K': r.get('K'),
            'reason': r.get('reason'), 'start': r.get('start_bound'),
            'tables': [(t['vectors'], t['nodes'], t['edges'], t['maxh'], t['start_bound']) for t in r['tables']],
            'wstats': [(w['expanded'], w['stored'], w['omega']) for w in r.get('wstats', [])],
            'stats': r.get('stats') and (r['stats']['expanded'], r['stats']['stored']),
            'weighted': r.get('weighted')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    ap.add_argument('--mem', type=float, default=5.0)
    a = ap.parse_args()
    bad = 0
    t00 = time.time()
    for name, m, g, o, pk, W, K, cls, om, wcap, cap, stored in CASES:
        if a.only and a.only != name:
            continue
        vec = NG.refine(NG.base_vector(list(range(m, 0, -1)), 1 | (1 << g)), list(o))
        picks = [pk[0], o[0] + pk[1]]
        res, rss = {}, {}
        for which in ('narrow', 'wide'):
            (TW.use_wide if which == 'wide' else TW.use_narrow)()
            t0 = time.time()
            r = TO.run(vec, W, norm(cls), picks, K=K, cap=cap, mem_gb=a.mem, threads=4, omega=om or None,
                       wcap=wcap, then_exact=bool(om))
            res[which] = summary(r)
            st = r.get('stats') or (r.get('wstats') or [{}])[-1]
            rss[which] = (round(time.time() - t0, 1), st.get('rss_mb'))
        same = res['narrow'] == res['wide']
        hist = ''
        if isinstance(stored, tuple):
            # stored by a run before the weight-0 zero merge of lrxtree.c (18:44): its table had stored[1]
            # vectors; the count is comparable only if the current table has the same size
            if int(res['wide']['tables'][0][0]) != stored[1]:
                hist = ' stored %d from a pre-merge table of %d vectors (now %s): not comparable' % (
                    stored[0], stored[1], res['wide']['tables'][0][0])
                stored = None
            else:
                stored = stored[0]
        if stored is not None:
            got = res['wide']['stats'] and int(res['wide']['stats'][0])
            hist = ' stored %d -> %s' % (stored, 'match' if got == stored else 'DIFFERENT (%s)' % got)
            same = same and got == stored
        bad += not same
        s = res['wide']
        print('%-26s n=%d %s F=%s exp=%s w=%s | narrow %ss rss %s MB, wide %ss rss %s MB%s -> %s'
              % (name, len(vec), s['result'], s['F'] if s['F'] is not None else s['K'] or '',
                 s['stats'] and s['stats'][0], [x[0] for x in s['wstats']], rss['narrow'][0], rss['narrow'][1],
                 rss['wide'][0], rss['wide'][1], hist, 'IDENTICAL' if same else 'MISMATCH'), flush=True)
        if not same:
            print('   narrow %s\n   wide   %s' % (res['narrow'], res['wide']), flush=True)
        if s['result'] == 'INCOMPLETE':
            print('   %s' % s['reason'], flush=True)
    print('%d mismatches, %.0f s' % (bad, time.time() - t00))
    print('WIDE CROSSCHECK OK' if not bad else 'WIDE CROSSCHECK FAILED')


if __name__ == '__main__':
    main()
