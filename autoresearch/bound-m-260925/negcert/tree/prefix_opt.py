#!/usr/bin/env python3
"""Prefix re-optimization of known sorting words of one point state (lrxtree_wide --target, pure length).

    python3 prefix_opt.py M G o0,o1 --words FILE --classes 'a,b|..' [--kmin 20] [--kmax 80] [--cap N]
                          [--stop 3] [--bin PATH] [--tag X]

State v, T = T_m(n).  For a word w (length L) and position i, s_i = state after w[:i];
K_i = T + 1 - (L - i).  The oracle runs from s_i with the single terminal v (--target; tables rooted at v,
verified) and bound K_i:
  - FOUND u (a word from s_i to v, |u| < K_i): p = inverse(u) (reversed, L<->R) leads from v to s_i, and
    p + w[i:] sorts v with length <= T.  Re-verified with lrx_m.Profile and printed as a CERTIFYING word.
  - NONE: d(v, s_i) >= K_i, i.e. no word of v of length <= T continues with w[i:] after reaching s_i.
States are de-duplicated (largest K kept), run in increasing K, stopped after --stop consecutive INCOMPLETE.
Output: runs-wide/prefix-<tag>-<time>.json (refuses to overwrite).
"""
import argparse, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
from integrations import lrx_m as C  # noqa: E402
from suffix_opt import apply, enc  # noqa: E402


def inverse(u):
    return ''.join({'L': 'R', 'R': 'L', 'X': 'X'}[c] for c in reversed(u))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('m', type=int)
    ap.add_argument('g', type=int)
    ap.add_argument('origin')
    ap.add_argument('--words', action='append', required=True)
    ap.add_argument('--classes', action='append', required=True)
    ap.add_argument('--kmin', type=int, default=20)
    ap.add_argument('--kmax', type=int, default=80)
    ap.add_argument('--cap', type=int, default=30_000_000)
    ap.add_argument('--stop', type=int, default=3)
    ap.add_argument('--mem', type=float, default=5.0)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--bin', default=os.path.join(HERE, 'lrxtree_wide'))
    ap.add_argument('--tag', default='x')
    a = ap.parse_args()
    m, g = a.m, a.g
    o = [int(x) for x in a.origin.split(',')]
    v = C.refine(C.base_vector(list(range(m, 0, -1)), 1 | (1 << g)), o)
    n, T = len(v), C.budget(m, len(v) - m)
    words = set()
    for f in a.words:
        words.update(open(f).read().split())
    best = {}
    for w in sorted(words, key=len):
        if not C.is_root(apply(v, w)):
            continue
        for i in range(len(w) + 1):
            K = T + 1 - (len(w) - i)
            if a.kmin <= K <= a.kmax:
                key = tuple(apply(v, w[:i]))
                if key not in best or best[key][0] < K:
                    best[key] = (K, i, w)
    items = sorted(best.items(), key=lambda kv: kv[1][0])
    stamp = time.strftime('%H%M%S')
    bpath = os.path.join(HERE, 'runs-wide', 'prefix-%s-%s.batch' % (a.tag, stamp))
    opath = os.path.join(HERE, 'runs-wide', 'prefix-%s-%s.json' % (a.tag, stamp))
    if os.path.exists(bpath) or os.path.exists(opath):
        raise SystemExit('refusing to overwrite')
    with open(bpath, 'w') as fh:
        for st, (K, i, w) in items:
            fh.write('%d %s\n' % (K, ','.join(map(str, enc(st, m)))))
    cls_args = []
    for c in a.classes:
        cl = [None] * m
        for ci, p in enumerate(c.split('|')):
            for x in p.split(','):
                cl[int(x) - 1] = ci
        cls_args += ['--table', ','.join(map(str, cl))]
    cmd = ['nice', '-n', '19', a.bin, '--m', str(m), '--u0', ','.join(map(str, enc(v, m))), '--W', '1,0,0',
           '--target', ','.join(map(str, enc(v, m))), '--mem-gb', str(a.mem), '--threads', str(a.threads),
           '--cap', str(a.cap), '--batch', bpath, '--batch-stop', str(a.stop)] + cls_args
    print('v=%s n=%d T=%d words=%d states=%d K in [%d,%d]' % (v, n, T, len(words), len(items), a.kmin, a.kmax),
          flush=True)
    print(' '.join(cmd), flush=True)
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    recs, cur, header = [], None, []
    for line in proc.stdout:
        line = line.rstrip('\n')
        if line.startswith(('BATCH STOP', 'TABLE', 'START', 'RESULT ERROR')):
            print(line, flush=True)
            header.append(line)
        elif line.startswith('BATCH'):
            bi, K = map(int, line.split()[1:3])
            st, (K2, i, w) = items[bi]
            cur = {'idx': bi, 'K': K, 'i': i, 'state': list(st), 'word': w}
            recs.append(cur)
        elif line.startswith('STATS') and cur is not None:
            cur['stats'] = dict(kv.split('=', 1) for kv in line.split()[1:])
        elif line.startswith('RESULT') and cur is not None:
            p = line.split()
            cur['result'], cur['raw'] = p[1], line
            if p[1] == 'FOUND':
                print('  raw %s (state index %d, i=%d)' % (line, cur['idx'], cur['i']), flush=True)
                u = p[3]
                assert apply(cur['state'], u) == v, 'oracle word does not reach the target'
                full = inverse(u) + cur['word'][cur['i']:]
                prof = C.Profile(v, full, [0, o[0]])
                cur.update(F=int(p[2]), prefix=inverse(u), full=full, full_len=len(full), full_B=prof.base,
                           full_beta=list(prof.beta), sorts=C.is_root(apply(v, full)))
                print('*** CERTIFYING WORD: i=%d prefix %d -> full length %d, Profile B %d (T=%d) %s'
                      % (cur['i'], len(u), len(full), prof.base, T, full), flush=True)
            elif p[1] == 'INCOMPLETE':
                cur['reason'] = ' '.join(p[2:])
            print('  K=%d i=%d %s exp=%s %.0fs' % (cur['K'], cur['i'], cur['result'],
                                                  cur.get('stats', {}).get('expanded'), time.time() - t0), flush=True)
    proc.wait()
    out = {'m': m, 'g': g, 'origin': o, 'v': v, 'T': T, 'cmd': ' '.join(cmd), 'header': header,
           'n_states': len(items), 'records': recs, 'total_s': round(time.time() - t0),
           'found': [r for r in recs if r.get('result') == 'FOUND']}
    with open(opath, 'w') as fh:
        json.dump(out, fh, indent=1)
    print('done: %d searched, %d NONE, %d FOUND, %d INCOMPLETE; wrote %s'
          % (len(recs), sum(r.get('result') == 'NONE' for r in recs), len(out['found']),
             sum(r.get('result') == 'INCOMPLETE' for r in recs), opath), flush=True)


if __name__ == '__main__':
    main()
