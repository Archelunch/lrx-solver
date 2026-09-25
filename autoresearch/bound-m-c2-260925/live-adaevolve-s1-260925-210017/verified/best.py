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


def _lifts(v, t, perm, m, r, offset=0, rev_tie=False):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    mid = n // 2 + offset
    rem = [((target[p] - p + mid) % n) - mid for p in range(n)]
    q = sum(rem) // n
    indices = list(reversed(range(n))) if rev_tie else list(range(n))
    order = sorted(indices, key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep_weighted(v, rem, t, weight_zero=2.0, limit=4000):
    """Pure stdlib Dijkstra on cursor ring to avoid traversing zero blocks during sweeps."""
    import heapq
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0
    zeros_set = {p for p in range(n) if v[p] == 0}

    # Step costs: moving L from u to (u+1)%n crosses cell u; moving R to (u-1)%n crosses cell (u-1)%n
    def get_neighbors(u):
        r_step = (u + 1) % n
        w_r = 1.0 + (weight_zero if u in zeros_set else 0.0)
        l_step = (u - 1) % n
        w_l = 1.0 + (weight_zero if l_step in zeros_set else 0.0)
        return ((r_step, 'L', w_r), (l_step, 'R', w_l))

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
        if must_cross(c):
            cross(c)
            continue
        candidates = [x for x in range(n) if must_cross(x)]
        if not candidates:
            return None

        # Dijkstra from c to nearest candidate
        cand_set = set(candidates)
        dist = {c: 0.0}
        parent = {}
        pq = [(0.0, c)]
        target_found = None
        while pq:
            d_u, u = heapq.heappop(pq)
            if d_u > dist.get(u, float('inf')):
                continue
            if u in cand_set and u != c:
                target_found = u
                break
            for nxt_node, move, weight in get_neighbors(u):
                d_v = d_u + weight
                if d_v < dist.get(nxt_node, float('inf')):
                    dist[nxt_node] = d_v
                    parent[nxt_node] = (u, move)
                    heapq.heappush(pq, (d_v, nxt_node))

        if target_found is None:
            return None

        # Reconstruct path
        path_moves = []
        curr = target_found
        while curr != c:
            p_node, mv = parent[curr]
            path_moves.append(mv)
            curr = p_node
        path_moves.reverse()

        out.extend(path_moves)
        c = target_found
        cross(c)

    if any(rem):
        return None
    d = (t - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


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


def _hungarian(cost_matrix):
    """Pure Python Hungarian algorithm for linear sum assignment when scipy is unavailable."""
    n = len(cost_matrix)
    if n == 0:
        return [], []
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost_matrix[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    col_ind = [0] * n
    for j in range(1, n + 1):
        if p[j] > 0:
            col_ind[p[j] - 1] = j - 1
    return list(range(n)), col_ind


def _solve_assignment(cost_matrix):
    """Solve linear sum assignment using pure Python Hungarian."""
    _, col_ind = _hungarian(cost_matrix)
    return col_ind


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

    # Use linear_sum_assignment to find optimal zero-to-slot routings that minimize crossing imbalances
    zeros_pos = [p for p in range(n) if v[p] == 0]
    for t in range(n):
        target_zeros = [(t + m + j) % n for j in range(r)]
        # Cost matrix: model crossings between zero zi and all labels when mapped to target sj
        cost_mat = []
        for zi in zeros_pos:
            row = []
            for sj in target_zeros:
                # Count label crossing estimate: labels whose shortest cyclic path crosses zero's path
                crossings = 0
                for p in range(n):
                    if v[p] > 0:
                        lp_tgt = (t + v[p] - 1) % n
                        # Circle crossing condition for intervals (zi -> sj) and (p -> lp_tgt)
                        d_z = (sj - zi) % n
                        d_lp = (lp_tgt - p) % n
                        if ((p - zi) % n < d_z) != ((lp_tgt - zi) % n < d_z):
                            crossings += 1
                row.append(crossings)
            cost_mat.append(row)
        best_perm = _solve_assignment(cost_mat)
        if best_perm not in perms:
            perms.append(best_perm)

    offsets = (-1, 0, 1) if r <= 4 else (0, -1)
    rev_ties = (False, True) if r <= 3 else (False,)
    for t in range(n):
        for perm in perms:
            for off in offsets:
                for rev_tie in rev_ties:
                    rem = _lifts(v, t, perm, m, r, off, rev_tie)
                    modes = ['L', 'R', 'greedy', 'greedy_R']
                    for mode in modes:
                        w = _sweep(v, rem, t, mode)
                        if w is None:
                            continue
                        w = _reduce(w)
                        if w not in words and len(w) <= 4000:
                            cost = price(v, w)
                            if cost is not None:
                                words[w] = cost

                    # Slope-aware sweeps via Dijkstra
                    for wz in (1.5, 4.0):
                        w = _sweep_weighted(v, rem, t, weight_zero=wz)
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
    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - (m - 2) for b in beta])

    n_words = len(word_list)
    dim = k + 1

    selected_order = []
    seen = set()

    def add_idx(idx):
        if idx not in seen:
            seen.add(idx)
            selected_order.append(idx)

    # 1. Pure Python convex combination search using Frank-Wolfe algorithm on all words
    # Minimizing max_{d} sum lambda_i * costs[i][d]
    weights_dict = {}
    best_fw_combo = []
    # Start Frank-Wolfe from candidate words with low max cost
    best_init = min(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))
    cur_distrib = {best_init: 1.0}
    for it in range(1, 100):
        # Calculate current profile
        cur_prof = [sum(wt * costs[idx][d] for idx, wt in cur_distrib.items()) for d in range(dim)]
        # Worst violated dimension
        worst_d = max(range(dim), key=lambda d: cur_prof[d])
        best_w = min(range(n_words), key=lambda i: costs[i][worst_d])
        step = 2.0 / (it + 2)
        new_distrib = {idx: wt * (1.0 - step) for idx, wt in cur_distrib.items()}
        new_distrib[best_w] = new_distrib.get(best_w, 0.0) + step
        cur_distrib = {k: v for k, v in new_distrib.items() if v > 1e-4}

    for idx, wt in sorted(cur_distrib.items(), key=lambda kv: kv[1], reverse=True):
        add_idx(idx)

    # 2. Single best word overall
    best_single = min(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    add_idx(best_single)

    # 3. Check for best complementary pairs (w1, w2)
    candidate_set = set(sorted(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))[:50])
    candidate_set.update(sorted(range(n_words), key=lambda i: costs[i][0])[:30])
    for d in range(1, dim):
        candidate_set.update(sorted(range(n_words), key=lambda i: costs[i][d])[:10])
    candidates = list(candidate_set)

    best_pairs = []
    for i_idx, i in enumerate(candidates):
        for j in candidates[i_idx:]:
            val = max((costs[i][d] + costs[j][d]) * 0.5 for d in range(dim))
            best_pairs.append((val, i, j))
    best_pairs.sort(key=lambda item: item[0])
    for val, i, j in best_pairs[:6]:
        add_idx(i)
        add_idx(j)

    # 4. Best word on each coordinate
    for d in range(dim):
        best_d = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        add_idx(best_d)

    # 5. Multi-start Frank-Wolfe exploration
    starts = [best_single] + [min(range(n_words), key=lambda i: costs[i][d]) for d in range(dim)]
    for init_idx in starts:
        cur_val = list(costs[init_idx])
        for it in range(1, 40):
            worst_dim = max(range(dim), key=lambda d: cur_val[d] * (1.15 if d > 0 else 1.0))
            best_w_idx = min(range(n_words), key=lambda i: (costs[i][worst_dim], max(costs[i])))
            add_idx(best_w_idx)
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w_idx][d]

    # 6. Linear scalarizations
    import random
    rng = random.Random(42)
    for _ in range(30):
        weights = [rng.expovariate(1.0) if d == 0 else rng.expovariate(0.5) for d in range(dim)]
        idx = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
        add_idx(idx)

    # 7. Fill up by max violation and base cost B
    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    for idx in by_max:
        if len(selected_order) >= KEEP:
            break
        add_idx(idx)

    by_b = sorted(range(n_words), key=lambda i: (costs[i][0], max(costs[i])))
    for idx in by_b:
        if len(selected_order) >= KEEP:
            break
        add_idx(idx)

    res = [word_list[idx] for idx in selected_order[:KEEP]]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}
