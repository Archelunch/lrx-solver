#!/usr/bin/env python3
"""--target mode of lrxtree_wide against plain BFS (multiset vectors, L/R/X, zeros identical; a zero-zero swap
is a no-op, so it never shortens a path): random start/target pairs, m = 5..7 with 3..5 zeros (n <= 12), and
two n = 17 pairs at small distance.  Checks: C minimum = BFS distance, NONE at K = d, FOUND d at K = d + 1,
the word replays from start to target; target = canonical root reproduces the normal mode's minimum.
    python3 crosscheck_target.py [BIN]"""
import os, random, subprocess, sys, time
from collections import deque
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'lrxtree_wide')


def moves(v):
    yield 'L', v[1:] + v[:1]
    yield 'R', v[-1:] + v[:-1]
    yield 'X', (v[1], v[0]) + v[2:]


def bfs(s, t):
    d = {s: 0}
    q = deque([s])
    while q:
        x = q.popleft()
        if x == t:
            return d[x]
        for _, y in moves(x):
            if y not in d:
                d[y] = d[x] + 1
                q.append(y)


def run(m, s, t, K=None, target=True):
    enc = lambda v: ','.join(str(x - 1 if x else m + 2) for x in v)
    cls = ','.join(str(0 if x <= m // 2 else 1) for x in range(1, m + 1))
    cmd = [BIN, '--m', str(m), '--u0', enc(s), '--W', '1,0,0', '--threads', '2', '--mem-gb', '1', '--table', cls]
    if target:
        cmd += ['--target', enc(t)]
    if K is not None:
        cmd += ['--K', str(K)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.split('\n')
    res = [l for l in out if l.startswith('RESULT')][0].split()
    return res


def replay(s, w):
    v = s
    for ch in w:
        v = dict(moves(v))[ch]
    return v


rng = random.Random(260926)
bad = cases = 0
t0 = time.time()
for m, r in [(5, 3), (6, 3), (6, 4), (7, 4), (7, 5)]:
    for _ in range(6):
        base = list(range(1, m + 1)) + [0] * r
        s, t = tuple(rng.sample(base, len(base))), tuple(rng.sample(base, len(base)))
        d = bfs(s, t)
        a, b, c = run(m, s, t), run(m, s, t, K=d), run(m, s, t, K=d + 1)
        ok = a[1] == 'FOUND' and int(a[2]) == d and replay(s, a[3]) == t and b[1] == 'NONE' and c[1] == 'FOUND' \
            and int(c[2]) == d
        root = tuple(range(1, m + 1)) + (0,) * r
        e, f = run(m, s, root), run(m, s, root, target=False)
        ok &= e[1] == f[1] == 'FOUND' and e[2] == f[2]
        cases += 1
        bad += not ok
        print('m=%d n=%d d=%d C %s K=d %s K=d+1 %s root-target %s normal %s -> %s' % (
            m, len(s), d, a[2], b[1], c[2], e[2], f[2], 'ok' if ok else 'MISMATCH'), flush=True)
for trial in range(2):                                   # n = 17: target = a few random moves from the start
    m, r = 12, 5
    s = tuple(rng.sample(list(range(1, m + 1)) + [0] * r, m + r))
    t = s
    for _ in range(14 + 4 * trial):
        t = rng.choice([y for _, y in moves(t)])
    d = bfs(s, t)
    a, b = run(m, s, t), run(m, s, t, K=d)
    ok = a[1] == 'FOUND' and int(a[2]) == d and replay(s, a[3]) == t and b[1] == 'NONE'
    cases += 1
    bad += not ok
    print('m=%d n=%d d=%d C %s K=d %s -> %s' % (m, len(s), d, a[2], b[1], 'ok' if ok else 'MISMATCH'), flush=True)
print('%d cases, %d mismatches, %.0f s' % (cases, bad, time.time() - t0))
print('TARGET CROSSCHECK OK' if not bad else 'TARGET CROSSCHECK FAILED')
