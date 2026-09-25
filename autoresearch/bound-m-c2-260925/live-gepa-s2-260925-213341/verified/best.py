"""Lift-and-sweep certifier using exact Lemma 1 pricing and balanced LP selection."""

import itertools
import random

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ("LR", "RL", "XX"):
            out.pop()
        else:
            out.append(ch)
    return "".join(out)


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
            out.append("X")
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    while any(rem) and len(out) < limit:
        if mode.startswith("greedy"):
            dirs = (1, -1) if mode == "greedy" else (-1, 1)
            for dist in range(n):
                found = False
                for sgn in dirs:
                    pos = (c + sgn * dist) % n
                    if must_cross(pos):
                        out.append(("L" if sgn == 1 else "R") * dist)
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
        c = (c + (1 if mode == "L" else -1)) % n
    if any(rem):
        return None
    d = (t - c) % n
    out.append("L" * d if d <= n - d else "R" * (n - d))
    return "".join(out)


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
        if ch == "L":
            d += 1
            if a[c] < 0:
                cz[-a[c] - 1] += 1
            c = (c + 1) % n
        elif ch == "R":
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


def _get_perms(r):
    perms = []
    seen = set()

    def add(p):
        tup = tuple(p)
        if tup not in seen:
            seen.add(tup)
            perms.append(list(p))

    for s in range(r):
        add([(s + i) % r for i in range(r)])
        add([(s + r - 1 - i) % r for i in range(r)])

    if r <= 4:
        for p in itertools.permutations(range(r)):
            add(p)
        return perms

    # Add near-dihedral swaps (crucial for reversal & near-reversal orders)
    for s in range(r):
        for base in (
            [(s + i) % r for i in range(r)],
            [(s + r - 1 - i) % r for i in range(r)],
        ):
            for i in range(r - 1):
                sw = list(base)
                sw[i], sw[i + 1] = sw[i + 1], sw[i]
                add(sw)
            if r >= 6:
                sw2 = list(base)
                sw2[0], sw2[-1] = sw2[-1], sw2[0]
                add(sw2)

    if r == 5:
        all_p = list(itertools.permutations(range(r)))
        rng = random.Random(42)
        rng.shuffle(all_p)
        for p in all_p:
            add(p)
            if len(perms) >= 48:
                break
    elif r > 5:
        # Complementary anti-cyclic / reflected shifts
        rng = random.Random(42)
        bases = list(perms[: 2 * r])
        for b in bases:
            p = list(b)
            rng.shuffle(p)
            add(p)
            if len(perms) >= 64:
                break
    return perms


def pool(v):
    n, m = len(v), max(v)
    r = n - m
    words = {}
    perms = _get_perms(r)
    modes = ("L", "R", "greedy", "greedy_R")

    for t in range(n):
        for perm in perms:
            rem = _lifts(v, t, perm, m, r)
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


def _mwu_solve(costs, max_steps=200):
    N = len(costs)
    dim = len(costs[0])
    p = [1.0 / dim] * dim
    w_sum = [0.0] * N
    eta = 0.6
    for step in range(1, max_steps + 1):
        best_i = min(
            range(N), key=lambda i: sum(p[d] * costs[i][d] for d in range(dim))
        )
        w_sum[best_i] += 1.0
        losses = costs[best_i]
        max_l = max(losses)
        new_p = [
            p[d] * (2.718281828459045 ** (eta * (losses[d] - max_l)))
            for d in range(dim)
        ]
        tot = sum(new_p)
        if tot > 0:
            p = [x / tot for x in new_p]
        eta = 0.6 / (step**0.5)
    return w_sum


def certify(family):
    v = family["unit_base"]
    words = pool(v)
    if not words:
        return {"words": []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)

    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - (m - 2) for b in beta])

    n_words = len(word_list)
    dim = k + 1
    selected = set()

    # 1. MWU solver distribution
    w_counts = _mwu_solve(costs, max_steps=240)
    top_mwu = sorted(range(n_words), key=lambda i: w_counts[i], reverse=True)
    for idx in top_mwu:
        if w_counts[idx] > 0:
            selected.add(word_list[idx])
            if len(selected) >= 16:
                break

    # 2. Extreme words per slope coordinate and cost B
    for d in range(dim):
        best_idx = min(
            range(n_words), key=lambda i: (costs[i][d], max(costs[i]))
        )
        selected.add(word_list[best_idx])

    # 3. Targeted Frank-Wolfe runs focusing on hardest slope dimensions
    for d_target in range(dim):
        init_idx = min(
            range(n_words), key=lambda i: (costs[i][d_target], max(costs[i]))
        )
        cur_val = list(costs[init_idx])
        for it in range(1, 40):
            worst_d = max(
                range(dim),
                key=lambda d: cur_val[d] * (1.35 if d > 0 else 1.0),
            )
            best_idx = min(
                range(n_words),
                key=lambda i: (costs[i][worst_d], sum(costs[i])),
            )
            selected.add(word_list[best_idx])
            gamma = 2.0 / (it + 2)
            for d in range(dim):
                cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[
                    best_idx
                ][d]

    # 4. Anti-correlated / complementary pairing on slopes (key for reversal-orbits)
    curr_sel = list(selected)
    for idx_w in curr_sel:
        c_i = costs[word_list.index(idx_w)]
        comp_idx = min(
            range(n_words),
            key=lambda j: max(c_i[d] + costs[j][d] for d in range(1, dim)),
        )
        selected.add(word_list[comp_idx])
        if len(selected) >= 28:
            break

    # 5. Fill remaining slots by smallest maximal slope violation, then smallest B
    by_slope = sorted(
        range(n_words),
        key=lambda i: (max(costs[i][1:]), max(costs[i]), costs[i][0]),
    )
    for idx in by_slope:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
    for idx in by_max:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    res = sorted(
        list(selected),
        key=lambda w: (max(words[w][1]), words[w][0], sum(words[w][1])),
    )[:KEEP]
    return {"words": res}