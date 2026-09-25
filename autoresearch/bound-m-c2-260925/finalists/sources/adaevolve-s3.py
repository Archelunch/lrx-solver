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


def _lifts(v, t, perm, m, r, half=None):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    h = n // 2 if half is None else half
    rem = [((target[p] - p + h) % n) - h for p in range(n)]
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

    halves = [n // 2, (n - 1) // 2, (n + 1) // 2]
    for t in range(n):
        for perm in perms:
            for h in halves:
                rem = _lifts(v, t, perm, m, r, half=h)
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

    # Exact LP solve via scipy.optimize.linprog (HiGHS)
    lp_words = []
    try:
        from scipy.optimize import linprog

        # Variables: w_0..w_{n-1}, theta
        # Objective: minimize theta
        c_obj = [0.0] * n_words + [1.0]

        # Inequality constraints: sum(w_i * excess[i][d]) - theta <= 0
        # excess for B: B_i - (T + 0.999) (evaluator allows B < T + 1)
        # excess for slopes: beta_{i,j} - (m - 2)
        A_ub = []
        b_ub = []
        # Constraint for B
        row_B = [words[w][0] - (T + 0.999) for w in word_list] + [-1.0]
        A_ub.append(row_B)
        b_ub.append(0.0)
        # Constraints for each beta_j
        for j in range(k):
            row_beta = [words[w][1][j] - (m - 2) for w in word_list] + [-1.0]
            A_ub.append(row_beta)
            b_ub.append(0.0)

        # Equality constraint: sum(w_i) = 1
        A_eq = [[1.0] * n_words + [0.0]]
        b_eq = [1.0]

        bounds = [(0.0, 1.0)] * n_words + [(None, None)]

        res_lp = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        if res_lp.success:
            w_sol = res_lp.x[:n_words]
            for idx in sorted(range(n_words), key=lambda i: -w_sol[i]):
                if w_sol[idx] > 1e-6:
                    lp_words.append(idx)
                    selected.add(word_list[idx])

        # Also solve for pure slope minimax where B <= T + 0.999 is a strict constraint
        A_ub_s = []
        b_ub_s = []
        A_ub_s.append([words[w][0] - (T + 0.999) for w in word_list] + [0.0])
        b_ub_s.append(0.0)
        for j in range(k):
            A_ub_s.append([words[w][1][j] - (m - 2) for w in word_list] + [-1.0])
            b_ub_s.append(0.0)
        res_lp2 = linprog(c_obj, A_ub=A_ub_s, b_ub=b_ub_s, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        if res_lp2.success:
            w_sol2 = res_lp2.x[:n_words]
            for idx in sorted(range(n_words), key=lambda i: -w_sol2[i]):
                if w_sol2[idx] > 1e-6:
                    if idx not in lp_words:
                        lp_words.append(idx)
                    selected.add(word_list[idx])
    except Exception:
        pass

    # Multiplicative weights fallback / supplement
    y = [1.0 / dim] * dim
    for step in range(1, 301):
        best_i = min(range(n_words), key=lambda i: sum(y[d] * costs[i][d] for d in range(dim)))
        selected.add(word_list[best_i])
        c_best = costs[best_i]
        lr = (2.0 / (step + 10)) ** 0.5
        new_y = [y[d] * (2.718281828459045 ** (lr * c_best[d])) for d in range(dim)]
        sy = sum(new_y)
        y = [val / sy for val in new_y]

    # Deterministic priority ordering for remaining slots
    import random
    rng = random.Random(42)
    for _ in range(40):
        weights = [rng.expovariate(1.0) if d == 0 else rng.expovariate(0.5) for d in range(dim)]
        idx = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
        selected.add(word_list[idx])

    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    for idx in by_max:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    # Build final list prioritizing lp_words first so they are NEVER truncated
    ordered = []
    seen = set()
    for idx in lp_words:
        w = word_list[idx]
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    for w in sorted(selected, key=lambda w: (max(costs[word_list.index(w)]), costs[word_list.index(w)][0])):
        if w not in seen:
            seen.add(w)
            ordered.append(w)

    res = ordered[:KEEP]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}
