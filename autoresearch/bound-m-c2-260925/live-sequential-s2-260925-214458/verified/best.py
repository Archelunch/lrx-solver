"""Lift-and-sweep certifier with symmetric / alternating sweeps and LP-targeted complementary selection."""

import itertools
import random

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, perm, m, r, bias=0):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n + bias
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

    steps = 0
    while any(rem) and len(out) < limit:
        if mode == 'greedy':
            found = False
            for dist in range(n):
                for sgn in (1, -1):
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
        elif mode == 'greedy_R':
            found = False
            for dist in range(n):
                for sgn in (-1, 1):
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
        elif mode.startswith('alt'):
            # Alternate sweep direction every period steps
            period = int(mode[3:]) if len(mode) > 3 else n
            cur_dir = 1 if (steps // period) % 2 == 0 else -1
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            out.append('L' if cur_dir == 1 else 'R')
            c = (c + cur_dir) % n
            steps += 1
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
        perms = list(itertools.permutations(range(r)))[:36]
    else:
        cyclic = [[(s + i) % r for i in range(r)] for s in range(r)]
        rev_cyclic = [[(s + r - 1 - i) % r for i in range(r)] for s in range(r)]
        perms = cyclic + rev_cyclic

    # Complementary sweep modes: symmetric forward/backward, greedy, and alternating periods
    modes = ['L', 'R', 'greedy', 'greedy_R', f'alt{n}', f'alt{max(1, n // 2)}']
    biases = (0, 1, -1) if r <= 3 else (0,)

    for t in range(n):
        for perm in perms:
            for b in biases:
                rem = _lifts(v, t, perm, m, r, bias=b)
                for mode in modes:
                    w = _sweep(v, rem, t, mode)
                    if w is None:
                        continue
                    w = _reduce(w)
                    if len(w) <= 4000 and w not in words:
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
    s = m - 2

    n_words = len(word_list)
    dim = k + 1

    # Matrix C: rows = words, cols = [B - T, beta_0 - s, ..., beta_{k-1} - s]
    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - s for b in beta])

    selected = set()

    # 0. Add single-word certificates if any
    for i, c in enumerate(costs):
        if all(x <= 0 for x in c):
            selected.add(i)

    # 1. Best words for each individual coordinate and small-B candidates
    for d in range(dim):
        best_d = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected.add(best_d)
    top_b = sorted(range(n_words), key=lambda i: costs[i][0])[:10]
    for i in top_b:
        selected.add(i)

    # 2. Complementary pair search with continuous weight alpha in [0, 1]
    # Criterion 7: finding pairs where alpha*c_i + (1-alpha)*c_j <= 0 on all coords
    pair_pool = sorted(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))[:min(n_words, 220)]
    best_pairs = []
    for idx_a, i in enumerate(pair_pool):
        ci = costs[i]
        for j in pair_pool[idx_a:]:
            cj = costs[j]
            # Test convex combinations: alpha in {0.2, 0.33, 0.5, 0.67, 0.8}
            min_slack = float('inf')
            for alpha in (0.5, 0.4, 0.6, 0.333, 0.667, 0.25, 0.75):
                slack = max(alpha * ci[d] + (1.0 - alpha) * cj[d] for d in range(dim))
                if slack < min_slack:
                    min_slack = slack
            best_pairs.append((min_slack, i, j))
    best_pairs.sort(key=lambda x: x[0])
    for _, i, j in best_pairs[:24]:
        selected.add(i)
        selected.add(j)

    # 3. Dual Hedge / Multiplicative Weights with adaptive slope focus
    for init_bias in range(dim):
        weights = [1.0 / dim] * dim
        weights[init_bias] += 3.0
        tot = sum(weights)
        weights = [w / tot for w in weights]
        for _ in range(35):
            idx = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
            selected.add(idx)
            ci = costs[idx]
            weights = [weights[d] * (1.35 if ci[d] > 0 else 0.7) for d in range(dim)]
            tot = sum(weights)
            weights = [w / tot for w in weights]

    # 4. Frank-Wolfe complementary mixture search starting from various facets
    for start_d in range(dim):
        cur_w = min(range(n_words), key=lambda i: (costs[i][start_d], max(costs[i])))
        selected.add(cur_w)
        cur_val = list(costs[cur_w])
        for it in range(1, 45):
            worst_d = max(range(dim), key=lambda d: cur_val[d])
            cand = min(range(n_words), key=lambda i: costs[i][worst_d])
            selected.add(cand)
            gamma = 2.0 / (it + 2)
            cur_val = [(1.0 - gamma) * cur_val[d] + gamma * costs[cand][d] for d in range(dim)]

    # 5. Targeted Dirichlet scalarizations penalizing individual zero slopes
    rng = random.Random(1337)
    for _ in range(35):
        w_slopes = [rng.expovariate(0.3) for _ in range(k)]
        w_b = rng.expovariate(1.0)
        sw = [w_b] + w_slopes
        idx = min(range(n_words), key=lambda i: sum(sw[d] * costs[i][d] for d in range(dim)))
        selected.add(idx)

    # Prioritize selected words by minimum max-slack, then maximum slope, then B
    ranked = sorted(
        selected,
        key=lambda i: (max(costs[i]), max(costs[i][1:]), costs[i][0])
    )

    if len(ranked) < KEEP:
        extra = sorted(
            (i for i in range(n_words) if i not in selected),
            key=lambda i: (max(costs[i]), costs[i][0])
        )
        ranked.extend(extra[:KEEP - len(ranked)])

    return {'words': [word_list[i] for i in ranked[:KEEP]]}
