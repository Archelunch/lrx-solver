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

    lift_bases = []
    base1 = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    lift_bases.append(base1)
    if n % 2 == 0:
        base2 = [((target[p] - p + n // 2 - 1) % n) - (n // 2 - 1) for p in range(n)]
        if base2 != base1:
            lift_bases.append(base2)

    res = []
    for rem_base in lift_bases:
        q = sum(rem_base) // n
        if q == 0:
            if rem_base not in res:
                res.append(rem_base)
            continue
        for rev_tie in (False, True):
            rem = list(rem_base)
            order = sorted(range(n), key=lambda p: (rem[p], -p if rev_tie else p), reverse=q > 0)
            for p in order[:abs(q)]:
                rem[p] -= n if q > 0 else -n
            if rem not in res:
                res.append(rem)
    return res


def _sweep(v, rem, t, mode, c_start=0, limit=4000):
    n = len(v)
    a, rem = list(v), list(rem)
    out = []
    c = 0
    if c_start != 0:
        d = c_start % n
        out.append('L' * d if d <= n - d else 'R' * (n - d))
        c = c_start % n

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] or a[y]:
            out.append('X')
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    bounce_dir = 1 if mode == 'bounce_L' else -1
    bounce_steps = 0
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
        elif mode.startswith('bounce'):
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            # Step in current bounce direction
            step_ch = 'L' if bounce_dir == 1 else 'R'
            out.append(step_ch)
            c = (c + bounce_dir) % n
            bounce_steps += 1
            if bounce_steps >= n - 1:
                bounce_dir = -bounce_dir
                bounce_steps = 0
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
            for rem in _lifts(v, t, perm, m, r):
                for c_start in (0, t) if t != 0 else (0,):
                    for mode in ('L', 'R', 'greedy', 'greedy_R', 'bounce_L', 'bounce_R'):
                        w = _sweep(v, rem, t, mode, c_start=c_start)
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

    import math

    # Convex Hull boundary & Pareto frontier extraction
    hull_indices = set()

    # 1. 2D Lower Convex Hull projections: (B vs beta_j) for each zero j
    for j in range(1, dim):
        pts = sorted(range(n_words), key=lambda i: (costs[i][0], costs[i][j]))
        # Andrew's monotone chain algorithm for lower hull
        lower = []
        for p in pts:
            while len(lower) >= 2:
                p1, p2 = lower[-2], lower[-1]
                # cross product (p2 - p1) x (p - p1)
                dx1, dy1 = costs[p2][0] - costs[p1][0], costs[p2][j] - costs[p1][j]
                dx2, dy2 = costs[p][0] - costs[p1][0], costs[p][j] - costs[p1][j]
                if dx1 * dy2 - dy1 * dx2 <= 0:
                    lower.pop()
                else:
                    break
            lower.append(p)
        for idx in lower:
            hull_indices.add(idx)

    # 2. Multi-angle scalarization scans across complementary trade-off rays
    for j in range(1, dim):
        for ratio in (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0):
            best_idx = min(range(n_words), key=lambda i: costs[i][0] + ratio * costs[i][j])
            hull_indices.add(best_idx)

    # 3. Softmax Frank-Wolfe to find complementary mixtures for minimax cost
    for alpha in (1.5, 3.0):
        for start_mode in ('min_max', 'min_b'):
            if start_mode == 'min_max':
                cur_idx = min(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
            else:
                cur_idx = min(range(n_words), key=lambda i: (costs[i][0], max(costs[i])))
            cur_vec = list(costs[cur_idx])
            hull_indices.add(cur_idx)
            for it in range(1, 40):
                mx = max(cur_vec)
                exps = [math.exp(min(50.0, alpha * (v - mx))) for v in cur_vec]
                tot = sum(exps)
                weights = [e / tot for e in exps]
                best_i = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
                hull_indices.add(best_i)
                gamma = 2.0 / (it + 2)
                for d in range(dim):
                    cur_vec[d] = (1.0 - gamma) * cur_vec[d] + gamma * costs[best_i][d]

    # Coordinate minimizers
    for d in range(dim):
        hull_indices.add(min(range(n_words), key=lambda i: (costs[i][d], max(costs[i]))))

    # Prioritize vertices by minimax violation and lowest B
    ordered = sorted(hull_indices, key=lambda i: (max(costs[i]), costs[i][0], sum(costs[i])))
    selected_indices = list(ordered[:KEEP])

    # Fill remaining slots up to KEEP
    if len(selected_indices) < KEEP:
        by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
        for idx in by_max:
            if idx not in selected_indices:
                selected_indices.append(idx)
                if len(selected_indices) >= KEEP:
                    break

    res = [word_list[i] for i in selected_indices[:KEEP]]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}


_certify_c2 = certify


def certify(family):
    out = _certify_c2(family)
    leaf = {"words": out["words"], "origins": [1] * family["k"]}
    if "weights" in out:
        leaf["weights"] = out["weights"]
    return {"tree": leaf}
