#!/usr/bin/env python3
"""lrxtree_wide at n = 17..20 (the 128-bit range) against the pure-Python reference: near-sorted states with
m = 9..12 and up to 8 zeros in two blocks, small enough for negcert_general.raw_dijkstra (uncompressed, no
table).  Checks: C minimum = raw_dijkstra = negcert_general.price = lrx_m.Profile price of the returned word;
bounded search NONE at K = F and F at K = F + 1."""
import json, math, os, random, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
import treeoracle_wide as TW
import treeoracle as TO
from integrations import lrx_m as C
NG = TO.NG
TW.use_wide()


def classes_for(m, n, zc):
    """coarsest-to-finer label partitions (consecutive runs); finest whose table fits 2e7 nodes"""
    best = [list(range(m, 0, -1))]
    for k in (2, 3, 4):
        sizes = [m // k + (i < m % k) for i in range(k)]
        N = math.factorial(n) // math.prod(math.factorial(s) for s in sizes + zc)
        if N * 6 < 2e7:
            parts, x = [], m
            for s in sizes:
                parts.append(list(range(x, x - s, -1)))
                x -= s
            best = parts
    return best


rng = random.Random(260926)
t0 = time.time()
bad = n_cases = skipped = 0
CONFIGS = [(9, 8), (10, 7), (11, 6), (12, 5), (12, 6), (12, 7), (12, 8), (11, 8)]
NCONF = int(sys.argv[1]) if len(sys.argv) > 1 else len(CONFIGS)
NTRIAL = int(sys.argv[2]) if len(sys.argv) > 2 else 4
for m, r in CONFIGS[:NCONF]:
    for trial in range(NTRIAL):
        a = rng.randint(1, r - 1)
        lab = list(range(1, m + 1))
        i = rng.randint(0, 3)                           # one adjacent transposition near the front
        lab[i], lab[i + 1] = lab[i + 1], lab[i]
        gap = m - trial % 3                             # second block 0..2 labels before the end
        vec = [0] * a + lab[:gap] + [0] * (r - a) + lab[gap:]
        blocks = NG.blocks_of(vec)
        for W in ((1, 0, 0), (1, 1, 0), (2, 3, 1), (1, 0, 3)) if gap == m else ((1, 0, 0),):  # weighted zeros
            # blow up raw_dijkstra's counter space on the gap m-1 states; those are checked at unit weights
            pk = (rng.randint(0, len(blocks[0]) - 1), rng.randint(0, len(blocks[1]) - 1))
            picks = [blocks[0][pk[0]], blocks[1][pk[1]]]
            zc = [1 if W[1] else 0, 1 if W[2] else 0]
            zc.append(r - sum(zc))
            cl = classes_for(m, len(vec), zc)
            rr = TO.run(vec, W, [cl], picks, threads=2, mem_gb=2)
            try:                                        # reference in a subprocess, 90 s limit: SKIPPED, not ok
                G = json.loads(subprocess.run(
                    [sys.executable, '-c', 'import sys, json; sys.path.insert(0, %r); import treeoracle as TO; '
                     'print(json.dumps(TO.NG.raw_dijkstra(%r, %r, %r)))' % (HERE, vec, W, picks)],
                    capture_output=True, text=True, timeout=90).stdout)
            except subprocess.TimeoutExpired:
                skipped += 1
                print('n=%d m=%d vec=%s W=%s: reference over 90 s -> SKIPPED' % (
                    len(vec), m, ''.join('%x' % x for x in vec), W), flush=True)
                continue
            prof = C.Profile(vec, rr['word'], picks)
            Fl = W[0] * prof.base + W[1] * prof.beta[0] + W[2] * prof.beta[1]
            r1 = TO.run(vec, W, [cl], picks, K=G, threads=2, mem_gb=2)
            r2 = TO.run(vec, W, [cl], picks, K=G + 1, threads=2, mem_gb=2)
            ok = rr['F'] == G == rr['Fw'] == Fl and r1['result'] == 'NONE' and r2.get('F') == G
            n_cases += 1
            bad += not ok
            print('n=%d m=%d vec=%s picks=%s W=%s classes=%d: C %s raw %s Profile %s K=F %s K=F+1 %s -> %s'
                  % (len(vec), m, ''.join('%x' % x for x in vec), picks, W, len(cl), rr['F'], G, Fl, r1['result'],
                     r2.get('F'), 'ok' if ok else 'MISMATCH'), flush=True)
print('%d cases checked, %d mismatches, %d skipped (reference timeout), %.0f s' % (n_cases, bad, skipped, time.time() - t0))
print('CROSSCHECK N17 OK' if not bad else 'CROSSCHECK N17 FAILED')
