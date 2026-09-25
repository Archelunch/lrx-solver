# First sequential proposer prompt, seed 1 (bound-m-c2-260925)

Captured offline through the mock (no provider call). Only development families (m = 9, 10) appear; the validation (m = 11) and holdout (m = 11, 12) sets are never loaded by an engine.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `b6798138963963bd31c0262ddee15f3870cccc356b05438514fc047aef343bb0`
- Message roles: ['system', 'user']
- Client request fields: model `gemini-3.8-flash`, max_tokens `8192`, reasoning_effort `None`
- Captured from: `capture-sequential-s1/request-0001.json`
- A live run halts before its first model request if these messages hash differently.

## Message 1: system

``````text
Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of nonempty gaps (gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have l_j >= 1 zeros in the j-th gap of S, and its unit base has exactly one zero per gap. The candidate source must define certify(family) -> {'words': [...]} returning 1..32 words over L, R, X (at most 4000 letters each) that sort the unit base to (1, ..., m, 0, ..., 0) and never swap two zeros; optional 'weights' (rational strings) and 'note' are only reported. The trusted evaluator prices each word with the research group's Lemma 1 (exact, the same for every m): a word stretches to every block length, |W(z)| <= B + sum_j beta_j z_j with z_j = l_j - 1, B = (number of X) + sum over segments of |net rotation|, beta_j = 2 * (X letters touching block j) + sum over segments of |signed crossings of block j|, where a segment ends at every X. It then solves an exact LP over your words: the family is CERTIFIED when some mixture has weighted B < T + 1 and every weighted beta_j <= m - 2, with T = m(m+1)/2 + (k-1)(m-2) and k = |S|. That proves d(v) <= T_m(n) for every state of the family at every number of zeros. The binding constraint is usually the slope: sweeps cross zero blocks too often. Each family gets 3 s of CPU (module import 1 s); exact LP or search over a few hundred candidate words per family fits. Score per m: percentage of families certified (the worst m counts twice), plus small terms for valid output and a small gap. Development families are m = 9 and 10, reversal-type orders oversampled; the holdout has unseen families and an unseen m, so the program must work for any m with no tables: string constants over L/R/X of 24+ characters, literal containers with more than 64 elements and bytes constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. Do not read files, the network, or environment variables. Misses prove nothing.
``````

## Message 2: user

``````text
Improve this Python certify(family) program. The seed builds a pool of lift-and-sweep sorting words: every target rotation t, every zero routing (all k! permutations of the zeros onto the zero slots for k <= 4, the 2k dihedral ones for k >= 5) and four cursor sweeps (L, R, greedy, greedy_R); it prices each word by the Lemma 1 cost and returns the union of per-coordinate best words, Frank-Wolfe-like picks, random scalarizations and fill-ups, cut to 32. Return the entire replacement Python source in one fenced code block, with no prose and no docstring longer than a few lines. Raise the number of certified families, first on the worst m, by constructing words whose slopes beta_j stay at most m-2 (fewer labels crossing each zero block, fewer rotation passes across it) and by choosing the returned word set well. Most misses are reversal-orbit and near-reversal orders. Only development families are shown.

Current program:
```python
"""Lift-and-sweep family certifier (campaign 1 EvoX finalist, docstring rewritten for campaign 2).

certify(family) returns up to 32 sorting words for the unit base v of (a, S)
(one zero per nonempty gap; n = m + k; m = max(v), k = number of zeros; no
m-specific data). L moves a cursor one cell right, R one cell left, X swaps the
cells under the cursor and its right neighbor.

Pool (pool(v)). A lift fixes where every token goes: target rotation t in Z_n
(label x goes to cell t+x-1, zero slots are t+m..t+n-1) and a zero routing, a
permutation perm of the k interchangeable zeros onto the slots: all k! for
k <= 4, the 2k dihedral ones (cyclic shifts and reversed cyclic shifts) for
k >= 5. Each cell gets a displacement on the universal cover (the ring unrolled
to Z), normalized to sum 0. The routing changes A_j, the number of labels whose
path crosses zero j, and keeps the label-label part. For each lift four sweeps
route the cursor: L (always step right), R (always step left), greedy (jump to
the nearest pair that must cross, ties to the right) and greedy_R (ties to the
left). A pair crosses exactly when its displacement difference is >= 2; two
zeros never swap (they exchange displacements for free). A final shortest
rotation aligns the cursor; LR, RL and XX are cancelled.

Price (price(v, word)). The research group's Lemma 1 affine cost that the
evaluator uses: B = swaps + sum over segments |net rotation|, beta_j = 2 A_j +
sum over segments |signed crossings of zero j|, where a segment ends at every
X. The crossing part depends only on the lift; the sweep mode changes only the
travel term of B and the pass term of beta_j.

Selection (certify). Each word gets the cost vector
c = (B - T, beta_0 - s, ..., beta_{k-1} - s), T = m(m+1)/2 + (k-1)(m-2),
s = m - 2. The kept set is the union of: the best word on each coordinate;
k+2 Frank-Wolfe-like loops of 49 steps (each step adds the best word on the
currently worst coordinate, slopes weighted 1.15; the float weights are
discarded); 30 random scalarizations (random.Random(42)); fill-ups by max
violation, then by B. There is no single-word shortcut. The union is cut to 32
by list(set)[:32], so which words survive depends on string-hash iteration
order (the evaluator worker fixes PYTHONHASHSEED). The evaluator's exact LP
chooses the mixture: CERTIFIED when weighted B < T + 1 and every weighted
beta_j <= s. Campaign 1 misses concentrate in the reversal orbit (rotations of
m..1) and near-reversals, where every lift loads some zero with A_j near m/2.
"""

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, perm, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, t, mode, limit=4000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] or a[y]:
            out.append('X')
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    while any(rem) and len(out) < limit:
        if mode.startswith('greedy'):
            dirs = (1, -1) if mode == 'greedy' else (-1, 1)
            for dist in range(n):
                found = False
                for sgn in dirs:
                    pos = (c + sgn * dist) % n
                    if must_cross(pos):
                        out.append(('L' if sgn == 1 else 'R') * dist)
                        c = pos
                        found = True
                        break
                if found:
                    break
            else:
                return None
            cross(c)
            continue
        if must_cross(c):
            cross(c)
            if not any(rem):
                break
        out.append(mode)
        c = (c + (1 if mode == 'L' else -1)) % n
    if any(rem):
        return None
    d = (t - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def price(v, word):
    """Lemma 1 affine cost (B, beta) of word on the unit base v, or None if it does not
    sort v or swaps two zeros. Block j is the j-th zero of v (one zero per block)."""
    n, k = len(v), sum(1 for x in v if x == 0)
    a, j = [], 0
    for x in v:
        if x:
            a.append(x)
        else:
            j += 1
            a.append(-j)  # zero of block j-1
    segs, A, q, d, cz, c = [], [0] * k, 0, 0, [0] * k, 0
    for ch in word:
        if ch == 'L':
            d += 1
            if a[c] < 0:
                cz[-a[c] - 1] += 1
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            if a[c] < 0:
                cz[-a[c] - 1] -= 1
        else:
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x < 0 and y < 0:
                return None
            q += 1
            nxt = [0] * k
            if x < 0:
                cz[-x - 1] += 1
                A[-x - 1] += 1
            elif y < 0:
                A[-y - 1] += 1
                nxt[-y - 1] = -1
            segs.append((d, cz))
            d, cz = 0, nxt
            a[c], a[c2] = y, x
    segs.append((d, cz))
    fin = a[c:] + a[:c]
    m = n - k
    if fin[:m] != list(range(1, m + 1)):
        return None
    B = q + sum(abs(s) for s, _ in segs)
    beta = [2 * A[i] + sum(abs(z[i]) for _, z in segs) for i in range(k)]
    return B, beta


def pool(v):
    """{word: (B, beta)} over all sweep variants that sort v with no zero-zero swap."""
    import itertools
    n, m = len(v), max(v)
    r = n - m
    words = {}

    if r <= 4:
        perms = list(itertools.permutations(range(r)))
    else:
        perms = [[(s + i) % r for i in range(r)] for s in range(r)] + [
            [(s + r - 1 - i) % r for i in range(r)] for s in range(r)
        ]

    for t in range(n):
        for perm in perms:
            rem = _lifts(v, t, perm, m, r)
            for mode in ('L', 'R', 'greedy', 'greedy_R'):
                w = _sweep(v, rem, t, mode)
                if w is None:
                    continue
                w = _reduce(w)
                if w not in words and len(w) <= 4000:
                    cost = price(v, w)
                    if cost is not None:
                        words[w] = cost
    return words


def certify(family):
    v = family['unit_base']
    words = pool(v)
    if not words:
        return {'words': []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)

    # Cost vectors for each word: [B - T, beta_0 - (m-2), ..., beta_{k-1} - (m-2)]
    # Target is to make all components <= 0 (or minimize max component)
    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - (m - 2) for b in beta])

    n_words = len(word_list)
    dim = k + 1

    selected = set()

    # Always include top words for each coordinate
    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected.add(word_list[best_idx])

    # Multi-start Frank-Wolfe balancing to explore the LP Pareto frontier
    starts = [min(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))]
    for d in range(dim):
        starts.append(min(range(n_words), key=lambda i: (costs[i][d], max(costs[i]))))

    for init_idx in starts:
        selected.add(word_list[init_idx])
        cur_val = list(costs[init_idx])
        for it in range(1, 50):
            worst_dim = max(range(dim), key=lambda d: cur_val[d] * (1.15 if d > 0 else 1.0))
            best_w_idx = min(range(n_words), key=lambda i: (costs[i][worst_dim], max(costs[i])))
            selected.add(word_list[best_w_idx])
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w_idx][d]

    # Linear scalarization sampling on Pareto frontier
    import random
    rng = random.Random(42)
    for _ in range(30):
        weights = [rng.expovariate(1.0) if d == 0 else rng.expovariate(0.5) for d in range(dim)]
        idx = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
        selected.add(word_list[idx])

    # Also add words sorted by max violation, base cost B, and sum of slopes
    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    for idx in by_max:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    by_b = sorted(range(n_words), key=lambda i: (costs[i][0], max(costs[i])))
    for idx in by_b:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    res = list(selected)[:KEEP]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}

```

Evaluator feedback:
BOUND_PACKET_V2 (screen; development only; search signal, not proof)
this candidate m=9: certified 8/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 1.0, G 0.219; per k k2:0/1 k3:2/3 k4:1/1 k5:1/2 k6:0/2 k7:1/1 k8:1/2 k9:0/1 k10:2/2
this candidate m=10: certified 12/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 1.75, G 0.215; per k k2:0/2 k3:2/2 k4:2/2 k5:1/1 k6:1/1 k7:1/2 k8:1/1 k9:2/2 k10:1/1 k11:1/1
this candidate combined 120.1065; best so far: screen 120.1065 (20/30 certified); full development 212/303 certified (m=9: 94, m=10: 118), worst gap 2.85
seed full development: m=9 94/153, m=10 118/150
POOL: empty so far (valid words of accepted candidates enter after their evaluation; development only). Later packets report pool alone vs pool + your words (pool_gain).
- m10-mask528-labels9.8.7.6.5.4.2.3.1.10 (near_rev) m=10 k=2 mask=528 gaps=[4, 9] unit_base=[9, 8, 7, 6, 0, 5, 4, 2, 3, 1, 0, 10] T=63 s=8: NO_CERTIFICATE g=1.75
  order class: near_rev; reversal orbit: no
  gap-LP mixture: Bbar 64.0 vs T+1=64; weighted slopes (j:gap:slope:excess[*=tight]) 0:4:6.75:-1.25 1:9:9.75:1.75*
  bound: d(v) <= T_m(n) + floor((1) + 7/4*(r-k))
- m10-mask1025-labels10.9.8.7.6.5.4.3.2.1 (tight) m=10 k=2 mask=1025 gaps=[0, 10] unit_base=[0, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0] T=63 s=8: NO_CERTIFICATE g=1.0
  order class: tight; reversal orbit: yes
  binding at gap-LP optimum: slope j=0 (gap 0) +1.0; base pinned at T+1
  best single word 19: B=64 (T+1=64) crossing profile A=[4, 4] rot passes=[1, 0] beta=[9, 8] vs s=8
  gap-LP mixture: Bbar 64.0 vs T+1=64; weighted slopes (j:gap:slope:excess[*=tight]) 0:0:9.0:1.0* 1:10:8.0:0.0
  bound: d(v) <= T_m(n) + floor((1) + 1*(r-k))
- m9-mask656-labels432198765 (rev_rot) m=9 k=3 mask=656 gaps=[4, 7, 9] unit_base=[4, 3, 2, 1, 0, 9, 8, 7, 0, 6, 5, 0] T=59 s=7: NO_CERTIFICATE g=1.0
  order class: rev_rot; reversal orbit: yes
  binding at gap-LP optimum: slope j=0 (gap 4) +1.0; base pinned at T+1
  best single word 14: B=55 (T+1=60) crossing profile A=[3, 0, 2] rot passes=[2, 1, 3] beta=[8, 1, 7] vs s=7
  gap-LP mixture: Bbar 60.0 vs T+1=60; weighted slopes (j:gap:slope:excess[*=tight]) 0:4:8.0:1.0* 1:7:6.0:-1.0 2:9:4.5:-2.5
  bound: d(v) <= T_m(n) + floor((1) + 1*(r-k))
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.
Hint (research group's m=8 proof, REVERSAL-OBSTACLE.md section 2): of the 4088 reversal-orbit families (rotations of 8..1, all masks), 4054 closed with one mixture (criterion 7) and 34 needed piecewise tree certificates split on block lengths.
The m=8 analogue of the reversal with zeros in the leading and trailing gap closed with two words weighted 1/2: B 43 with slopes (5,4) and B 41 with slopes (7,6).
This contract scores one mixture only, so return complementary words whose average keeps every slope <= m-2 (mirrored crossing profiles), not many near-copies of one best word.

Provide ONLY the complete new program within ```python ... ``` blocks.
``````
