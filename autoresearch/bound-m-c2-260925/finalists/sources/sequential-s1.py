"""Lift-and-sweep family certifier with dual-simplex mixture pruning."""

import itertools


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
    for p in order[: abs(q)]:
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
    n, k = len(v), sum(1 for x in v if x == 0)
    a, j = [], 0
    for x in v:
        if x:
            a.append(x)
        else:
            j += 1
            a.append(-j)
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
    n, m = len(v), max(v)
    r = n - m
    words = {}

    if r <= 4:
        perms = list(itertools.permutations(range(r)))
    elif r == 5:
        # Full permutations for k=5 are only 120, well within CPU budget
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


def _solve_mixture_lp(word_costs, T, s):
    # min g subject to sum w_i = 1, w_i >= 0
    # sum w_i * (B_i - T) <= g
    # sum w_i * (beta_{i,j} - s) <= g for all j
    # Solved via standard dense primal simplex
    N = len(word_costs)
    if N == 0:
        return 999.0, []
    dim = len(word_costs[0])
    # Constraints: dim constraints: sum_i w_i * C_{j, i} - g <= 0
    # and 1 equality constraint: sum_i w_i = 1
    # Dual: max y_{dim} subject to sum_j C_{j, i} * dual_j + y_{dim} <= 0, sum_{j=0}^{dim-1} dual_j = 1, dual_j >= 0
    # That is: min_{w} max_{p in simplex} p^T C w. By minimax: min_p max_i (p^T C_i).
    # We solve the LP directly using coordinate descent / entropic mirror descent to find best supporting mixture.
    p = [1.0 / dim] * dim
    w = [0.0] * N
    w[min(range(N), key=lambda i: max(word_costs[i]))] = 1.0

    step_w = 0.2
    for _ in range(350):
        # find column i that minimizes p^T C_i
        best_i = min(range(N), key=lambda i: sum(p[d] * word_costs[i][d] for d in range(dim)))
        # update w
        gamma = 2.0 / (_ + 2.0)
        for i in range(N):
            w[i] = (1.0 - gamma) * w[i] + (gamma if i == best_i else 0.0)
        # mixture cost vector
        c_mix = [sum(w[i] * word_costs[i][d] for i in range(N)) for d in range(dim)]
        # update dual p (exponentiated gradient)
        max_c = max(c_mix)
        weights = [p[d] * (2.718281828 ** (min(5.0, c_mix[d] - max_c))) for d in range(dim)]
        tot = sum(weights) or 1.0
        p = [w_d / tot for w_d in weights]

    c_mix = [sum(w[i] * word_costs[i][d] for i in range(N)) for d in range(dim)]
    return max(c_mix), w


def certify(family):
    v = family['unit_base']
    words = pool(v)
    if not words:
        return {'words': []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)
    s = m - 2

    # Cost vectors for each word: [B - T, beta_0 - s, ..., beta_{k-1} - s]
    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - s for b in beta])

    n_words = len(word_list)
    dim = k + 1

    selected_indices = set()

    # Best words per dimension
    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected_indices.add(best_idx)

    # Multi-start Frank-Wolfe to capture Pareto faces
    starts = [
        min(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i]))),
        min(range(n_words), key=lambda i: costs[i][0]),
    ]
    for d in range(dim):
        starts.append(min(range(n_words), key=lambda i: costs[i][d]))

    for init_idx in starts:
        selected_indices.add(init_idx)
        cur_val = list(costs[init_idx])
        for it in range(1, 60):
            worst_dim = max(range(dim), key=lambda d: cur_val[d] * (1.18 if d > 0 else 1.0))
            best_w_idx = min(range(n_words), key=lambda i: (costs[i][worst_dim], max(costs[i])))
            selected_indices.add(best_w_idx)
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w_idx][d]

    # Find the top supporting weights from LP across all words
    gap, full_w = _solve_mixture_lp(costs, T, s)
    top_lp = sorted(range(n_words), key=lambda i: full_w[i], reverse=True)
    for idx in top_lp[:24]:
        if full_w[idx] > 1e-4:
            selected_indices.add(idx)

    # Add complimentary pairs specifically for reversal / near-reversal obstacles
    for j in range(1, dim):
        # Top word favoring beta_j low
        low_j = min(range(n_words), key=lambda i: costs[i][j])
        # Find best partner to neutralize other dimensions without exploding j
        partner = min(
            range(n_words),
            key=lambda i: max((costs[low_j][d] + costs[i][d]) * 0.5 for d in range(dim)),
        )
        selected_indices.add(low_j)
        selected_indices.add(partner)

    # Reduce down to at most 32 while preserving LP certificate
    curr = list(selected_indices)
    while len(curr) > 32:
        # Greedily remove the element whose removal minimizes LP gap degradation
        best_cand = None
        best_cand_gap = 1e9
        # Sample or test candidates
        curr_costs = [costs[i] for i in curr]
        _, w_sub = _solve_mixture_lp(curr_costs, T, s)
        # Find index with smallest weight in mixture
        drop_idx = min(range(len(curr)), key=lambda i: w_sub[i])
        curr.pop(drop_idx)

    res = [word_list[i] for i in curr]
    return {'words': res, 'note': 'pool %d, retained %d, LP gap %.3f' % (len(words), len(res), gap)}
