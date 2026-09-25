"""Lift-and-sweep certifier with complementary sweeps for LRX sorting words."""

import itertools
import math
import random
import time

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, perm, m, r, shift=0):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n + shift
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, t, mode, limit=3500):
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
        elif mode.startswith('bounce'):
            # Bounce between forward and backward sweep to balance zero crossings
            b_dir = 1 if mode == 'bounce_L' else -1
            found = False
            for step in range(n):
                pos = (c + b_dir * step) % n
                if must_cross(pos):
                    out.append(('L' if b_dir == 1 else 'R') * step)
                    c = pos
                    found = True
                    break
            if not found:
                for step in range(n):
                    pos = (c - b_dir * step) % n
                    if must_cross(pos):
                        out.append(('R' if b_dir == 1 else 'L') * step)
                        c = pos
                        found = True
                        break
            if not found:
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


def pool(v, start_time, time_budget=2.2):
    n, m = len(v), max(v)
    r = n - m
    words = {}

    if r <= 4:
        perms = list(itertools.permutations(range(r)))
    else:
        perms = [[(s + i) % r for i in range(r)] for s in range(r)] + [
            [(s + r - 1 - i) % r for i in range(r)] for s in range(r)
        ]

    shifts = (0, 1, -1, 2, -2) if r <= 3 else (0, 1, -1)
    modes = ('L', 'R', 'greedy', 'greedy_R', 'bounce_L', 'bounce_R')

    for t in range(n):
        if time.time() - start_time > time_budget:
            break
        for perm in perms:
            for sh in shifts:
                rem = _lifts(v, t, perm, m, r, sh)
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


def _solve_mixture_lp(costs, dim, iters=400):
    n = len(costs)
    if n == 0:
        return []
    w = [1.0 / n] * n
    y = [1.0 / dim] * dim
    w_sum = [0.0] * n
    eta_w = math.sqrt(math.log(n) / iters) if n > 1 else 0.1
    eta_y = math.sqrt(math.log(dim) / iters)

    for _ in range(iters):
        Cy = [sum(costs[i][d] * y[d] for d in range(dim)) for i in range(n)]
        wC = [sum(w[i] * costs[i][d] for i in range(n)) for d in range(dim)]

        for i in range(n):
            w_sum[i] += w[i]

        min_Cy = min(Cy)
        w = [w[i] * math.exp(-eta_w * (Cy[i] - min_Cy)) for i in range(n)]
        sw = sum(w)
        w = [wi / sw for wi in w]

        max_wC = max(wC)
        y = [y[d] * math.exp(eta_y * (wC[d] - max_wC)) for d in range(dim)]
        sy = sum(y)
        y = [yd / sy for yd in y]

    tot = sum(w_sum)
    return [wi / tot for wi in w_sum]


def certify(family):
    start_time = time.time()
    v = family['unit_base']
    words = pool(v, start_time)
    if not words:
        return {'words': []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)

    costs = []
    for w in word_list:
        B, beta = words[w]
        # Normalised excess vector: [B - (T+1), beta_0 - (m-2), ...]
        costs.append([B - (T + 1.0)] + [b - (m - 2.0) for b in beta])

    n_words = len(word_list)
    dim = k + 1
    selected = set()

    # Complementary pairs: directly check 2-mixtures (w_1 + w_2)/2
    cand_indices = sorted(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))[:min(120, n_words)]
    for d in range(dim):
        dim_sorted = sorted(range(n_words), key=lambda i: costs[i][d])[:10]
        cand_indices.extend(dim_sorted)
    cand_indices = list(set(cand_indices))

    best_pairs = []
    for i_idx, i in enumerate(cand_indices):
        ci = costs[i]
        for j in cand_indices[i_idx:]:
            cj = costs[j]
            excess = max((ci[d] + cj[d]) * 0.5 for d in range(dim))
            avg_sum = sum((ci[d] + cj[d]) * 0.5 for d in range(dim))
            best_pairs.append((excess, avg_sum, i, j))
    best_pairs.sort()

    for _, _, i, j in best_pairs[:14]:
        selected.add(word_list[i])
        selected.add(word_list[j])

    # Per-coordinate bests (pure slope minimization on each zero block)
    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected.add(word_list[best_idx])

    # MWU mixture LP over full pool
    mixture_w = _solve_mixture_lp(costs, dim, iters=400)
    top_lp = sorted(range(n_words), key=lambda i: mixture_w[i], reverse=True)
    for idx in top_lp[:min(20, n_words)]:
        if mixture_w[idx] > 1e-5:
            selected.add(word_list[idx])

    # Frank-Wolfe combinations with emphasis on tight slope blocks
    starts = [min(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))]
    for d in range(dim):
        starts.append(min(range(n_words), key=lambda i: (costs[i][d], max(costs[i]))))

    for init_idx in starts:
        selected.add(word_list[init_idx])
        cur_val = list(costs[init_idx])
        for it in range(1, 40):
            worst_dim = max(range(dim), key=lambda d: cur_val[d] * (1.5 if d > 0 else 1.0))
            best_w_idx = min(range(n_words), key=lambda i: (costs[i][worst_dim], max(costs[i])))
            selected.add(word_list[best_w_idx])
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w_idx][d]

    # Fill up with lowest max excess
    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i]), costs[i][0]))
    for idx in by_max:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    res = list(selected)[:KEEP]
    return {'words': res, 'note': f'pool {len(words)}, selected {len(res)}'}
