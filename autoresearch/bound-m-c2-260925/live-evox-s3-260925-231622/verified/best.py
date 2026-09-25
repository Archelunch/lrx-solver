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


def _lifts(v, t, perm, m, r, off=0, rev_tie=False):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    mid = n // 2 + off
    rem = [((target[p] - p + mid) % n) - mid for p in range(n)]
    q = sum(rem) // n
    if rev_tie:
        order = sorted(range(n), key=lambda p: (rem[p], -p if q > 0 else p), reverse=q > 0)
    else:
        order = sorted(range(n), key=lambda p: (rem[p], p if q > 0 else -p), reverse=q > 0)
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
        if mode.startswith('scan'):
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            d_dir = 1 if mode == 'scan_L' else -1
            ahead = any(must_cross((c + d_dir * s) % n) for s in range(1, n // 2 + 1))
            if not ahead:
                mode = 'scan_R' if mode == 'scan_L' else 'scan_L'
                d_dir = -d_dir
            out.append('L' if d_dir == 1 else 'R')
            c = (c + d_dir) % n
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

    modes = ('L', 'R', 'greedy', 'greedy_R', 'scan_L', 'scan_R')
    offsets = (-2, -1, 0, 1, 2) if r <= 2 else ((-1, 0, 1) if r <= 3 else ((0, 1) if r <= 5 else (0,)))
    tie_variants = (False, True) if r <= 3 else (False,)
    for t in range(n):
        for perm in perms:
            for off in offsets:
                for rev_tie in tie_variants:
                    rem = _lifts(v, t, perm, m, r, off, rev_tie)
                    for mode in modes:
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

    # Direct smooth minimax optimization via Frank-Wolfe with LogSumExp gradient.
    # Evaluator accepts when Bbar < T + 1 (i.e. Bbar - T < 1.0) and beta_bar_j <= m - 2.
    import math

    target_offset = [0.95] + [0.0] * k
    M = [[costs[i][d] - target_offset[d] for i in range(n_words)] for d in range(dim)]

    best_mixture_words = []
    best_val = float('inf')

    for eta in (4.0, 10.0, 25.0):
        cur_idx = min(range(n_words), key=lambda i: max(M[d][i] for d in range(dim)))
        cur_vec = [M[d][cur_idx] for d in range(dim)]
        cur_weights = {cur_idx: 1.0}

        for it in range(1, 80):
            max_v = max(cur_vec)
            exps = [math.exp(min(60.0, eta * (cur_vec[d] - max_v))) for d in range(dim)]
            sum_e = sum(exps)
            grad = [e / sum_e for e in exps]

            best_i = min(range(n_words), key=lambda i: sum(grad[d] * M[d][i] for d in range(dim)))

            gamma = 2.0 / (it + 2)
            for k_w in cur_weights:
                cur_weights[k_w] *= (1.0 - gamma)
            cur_weights[best_i] = cur_weights.get(best_i, 0.0) + gamma

            for d in range(dim):
                cur_vec[d] = (1.0 - gamma) * cur_vec[d] + gamma * M[d][best_i]

            val = max(cur_vec)
            if val < best_val:
                best_val = val
                # Keep significant words ordered by weight descending
                top_fw = sorted([idx for idx, w in cur_weights.items() if w > 0.015],
                                key=lambda idx: cur_weights[idx], reverse=True)
                best_mixture_words = top_fw

    selected = []
    seen = set()

    def add_idx(idx):
        if idx not in seen and len(selected) < KEEP:
            seen.add(idx)
            selected.append(word_list[idx])

    # 1. Best mixture support words with significant weights from Frank-Wolfe
    for idx in best_mixture_words:
        add_idx(idx)

    # 2. Extreme words on each coordinate (slopes and base cost)
    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        add_idx(best_idx)

    # 3. Explicit complementary pairs (criterion 7 mixtures)
    top_candidates = set()
    for d in range(dim):
        top_candidates.update(sorted(range(n_words), key=lambda i: costs[i][d])[:8])
    top_candidates.update(sorted(range(n_words), key=lambda i: max(costs[i]))[:10])
    top_cand_list = list(top_candidates)
    best_pairs = sorted(
        [(i, j) for idx_a, i in enumerate(top_cand_list) for j in top_cand_list[idx_a:]],
        key=lambda pair: (max((costs[pair[0]][d] + costs[pair[1]][d]) / 2.0 - target_offset[d] for d in range(dim)),
                          costs[pair[0]][0] + costs[pair[1]][0])
    )
    for i, j in best_pairs[:12]:
        add_idx(i)
        add_idx(j)

    # 4. Scalarization sampling to capture complementary trade-offs
    import random
    rng = random.Random(42)
    for _ in range(50):
        weights = [rng.expovariate(1.0) if d == 0 else rng.expovariate(0.3) for d in range(dim)]
        idx = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
        add_idx(idx)

    # 5. Fill remaining with lowest max cost and lowest base cost
    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    for idx in by_max:
        add_idx(idx)

    by_b = sorted(range(n_words), key=lambda i: (costs[i][0], max(costs[i])))
    for idx in by_b:
        add_idx(idx)

    res = selected[:KEEP]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}
