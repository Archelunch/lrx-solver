"""Certify families of LRX sorting problems using expanded sweeps and LP mixture selection."""

import itertools


def _reduce(w):
    out = []
    for ch in w:
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

    if mode in ('L', 'R'):
        step = 1 if mode == 'L' else -1
        while any(rem) and len(out) < limit:
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            out.append(mode)
            c = (c + step) % n
    elif mode in ('greedy', 'greedy_R'):
        dirs = (1, -1) if mode == 'greedy' else (-1, 1)
        while any(rem) and len(out) < limit:
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
    elif mode in ('bounce_L', 'bounce_R'):
        cur_dir = 1 if mode == 'bounce_L' else -1
        stuck = 0
        while any(rem) and len(out) < limit and stuck < 2 * n:
            if must_cross(c):
                cross(c)
                stuck = 0
                if not any(rem):
                    break
            nxt = (c + cur_dir) % n
            if not any(must_cross((c + cur_dir * d) % n) for d in range(1, n // 2 + 1)):
                cur_dir = -cur_dir
            out.append('L' if cur_dir == 1 else 'R')
            c = (c + cur_dir) % n
            stuck += 1
    elif mode in ('alt_L', 'alt_R'):
        cur_dir = 1 if mode == 'alt_L' else -1
        passes = 0
        while any(rem) and len(out) < limit and passes < 4 * n:
            crossed = False
            for _ in range(n):
                if must_cross(c):
                    cross(c)
                    crossed = True
                    if not any(rem):
                        break
                out.append('L' if cur_dir == 1 else 'R')
                c = (c + cur_dir) % n
            cur_dir = -cur_dir
            passes += 1
            if not crossed and any(rem):
                break
    elif mode.startswith('window_'):
        w_size = int(mode.split('_')[1])
        passes = 0
        while any(rem) and len(out) < limit and passes < 6 * n:
            crossed = False
            for d in range(w_size):
                pos = (c + d) % n
                if must_cross(pos):
                    out.append('L' * d)
                    c = pos
                    cross(c)
                    crossed = True
                    break
            if not crossed:
                out.append('R')
                c = (c - 1) % n
            passes += 1
    else:
        return None

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
        perms = list(itertools.permutations(range(r)))[:36]
    else:
        perms = [[(s + i) % r for i in range(r)] for s in range(r)] + [
            [(s + r - 1 - i) % r for i in range(r)] for s in range(r)
        ]

    modes = (
        'L',
        'R',
        'greedy',
        'greedy_R',
        'bounce_L',
        'bounce_R',
        'alt_L',
        'alt_R',
        'window_2',
        'window_3',
    )
    for t in range(n):
        for perm in perms:
            rem = _lifts(v, t, perm, m, r)
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


def _solve_mixture_lp(word_costs, iters=300):
    N = len(word_costs)
    if N == 0:
        return 999.0, []
    dim = len(word_costs[0])
    p = [1.0 / dim] * dim
    w = [0.0] * N
    w[min(range(N), key=lambda i: max(word_costs[i]))] = 1.0

    for it in range(iters):
        best_i = min(range(N), key=lambda i: sum(p[d] * word_costs[i][d] for d in range(dim)))
        gamma = 2.0 / (it + 2.0)
        for i in range(N):
            w[i] = (1.0 - gamma) * w[i] + (gamma if i == best_i else 0.0)
        c_mix = [sum(w[i] * word_costs[i][d] for i in range(N)) for d in range(dim)]
        max_c = max(c_mix)
        weights = [p[d] * (2.718281828 ** min(4.0, (c_mix[d] - max_c) * 1.5)) for d in range(dim)]
        tot = sum(weights) or 1.0
        p = [wd / tot for wd in weights]

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

    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - s for b in beta])

    n_words = len(word_list)
    dim = k + 1
    selected_indices = set()

    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected_indices.add(best_idx)

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
            worst_dim = max(range(dim), key=lambda d: cur_val[d] * (1.3 if d > 0 else 1.0))
            best_w_idx = min(range(n_words), key=lambda i: (costs[i][worst_dim], max(costs[i])))
            selected_indices.add(best_w_idx)
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w_idx][d]

    gap, full_w = _solve_mixture_lp(costs, iters=350)
    top_lp = sorted(range(n_words), key=lambda i: full_w[i], reverse=True)
    for idx in top_lp[:26]:
        if full_w[idx] > 1e-5:
            selected_indices.add(idx)

    for j in range(dim):
        low_j = min(range(n_words), key=lambda i: costs[i][j])
        selected_indices.add(low_j)
        partner = min(
            range(n_words),
            key=lambda i: max((costs[low_j][d] + costs[i][d]) * 0.5 for d in range(dim)),
        )
        selected_indices.add(partner)

    for i in list(selected_indices):
        compl = min(
            range(n_words),
            key=lambda j: max(costs[i][d] + costs[j][d] for d in range(dim)),
        )
        selected_indices.add(compl)

    curr = list(selected_indices)
    while len(curr) > 32:
        curr_costs = [costs[i] for i in curr]
        _, w_sub = _solve_mixture_lp(curr_costs, iters=150)
        drop_idx = min(range(len(curr)), key=lambda i: (w_sub[i], max(curr_costs[i])))
        curr.pop(drop_idx)

    res = [word_list[i] for i in curr]
    final_costs = [costs[i] for i in curr]
    final_gap, _ = _solve_mixture_lp(final_costs, iters=200)
    return {'words': res, 'note': 'pool %d, retained %d, LP gap %.3f' % (len(words), len(res), final_gap)}
