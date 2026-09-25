"""Lift-and-sweep certifier with multi-sweep modes, time bounds, and LP selection."""

import itertools
import time

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and (
            (out[-1] == "L" and ch == "R")
            or (out[-1] == "R" and ch == "L")
            or (out[-1] == "X" and ch == "X")
        ):
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


def _sweep(v, rem, t, mode, limit=3600):
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

    steps = 0
    while any(rem) and steps < limit:
        steps += 1
        if mode in ("greedy", "greedy_R", "greedy_bias"):
            dirs = (
                (1, -1)
                if mode == "greedy"
                else ((-1, 1) if mode == "greedy_R" else ((1, -1) if (steps % 2 == 0) else (-1, 1)))
            )
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

        if mode.startswith("bounce"):
            span = int(mode.split("_")[1]) if "_" in mode else 4
            sgn = 1 if ((steps // span) % 2 == 0) else -1
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            out.append("L" if sgn == 1 else "R")
            c = (c + sgn) % n
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


def pool(v, deadline):
    n, m = len(v), max(v)
    r = n - m
    words = {}

    perms = []
    if r <= 3:
        perms.extend(itertools.permutations(range(r)))
    else:
        for s in range(r):
            perms.append([(s + i) % r for i in range(r)])
            perms.append([(s - i) % r for i in range(r)])
        perms.append(list(range(r - 1, -1, -1)))
        perms.append(list(range(r)))

    seen_perms = []
    for p in perms:
        tp = tuple(p)
        if tp not in seen_perms:
            seen_perms.append(tp)

    modes = ("L", "R", "greedy", "greedy_R", "greedy_bias", "bounce_3")
    for t in range(n):
        if time.time() > deadline:
            break
        for perm in seen_perms:
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
                if time.time() > deadline:
                    break
            if time.time() > deadline:
                break
    return words


def certify(family):
    t_start = time.time()
    deadline = t_start + 2.45
    v = family["unit_base"]
    words = pool(v, deadline)
    if not words:
        return {"words": []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)
    s = m - 2
    dim = k + 1

    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - s for b in beta])

    n_words = len(word_list)
    selected = set()

    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected.add(word_list[best_idx])

    starts = [
        min(range(n_words), key=lambda i: max(costs[i])),
        min(range(n_words), key=lambda i: costs[i][0]),
    ]
    for d in range(1, dim):
        starts.append(min(range(n_words), key=lambda i: costs[i][d]))

    for s_idx in set(starts):
        for slope_weight in (1.0, 1.5, 2.2, 3.5):
            cur_val = list(costs[s_idx])
            selected.add(word_list[s_idx])
            for it in range(1, 80):
                weighted_vals = [cur_val[0]] + [cur_val[d] * slope_weight for d in range(1, dim)]
                worst_d = max(range(dim), key=lambda d: weighted_vals[d])
                best_w = min(range(n_words), key=lambda i: (costs[i][worst_d], max(costs[i])))
                selected.add(word_list[best_w])
                gamma = 2.0 / (it + 2)
                for d in range(dim):
                    cur_val[d] = (1.0 - gamma) * cur_val[d] + gamma * costs[best_w][d]

    sub_size = min(n_words, 80)
    sample_sub = sorted(range(n_words), key=lambda i: (max(costs[i]), sum(costs[i])))[:sub_size]
    pair_candidates = []
    for idx_a, i in enumerate(sample_sub):
        ci = costs[i]
        for j in sample_sub[idx_a:]:
            cj = costs[j]
            max_c = max(0.5 * (ci[d] + cj[d]) for d in range(dim))
            pair_candidates.append((max_c, i, j))
    pair_candidates.sort(key=lambda x: x[0])
    for _, i, j in pair_candidates[:40]:
        selected.add(word_list[i])
        selected.add(word_list[j])

    by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0], sum(costs[i])))
    for idx in by_max:
        if len(selected) >= KEEP:
            break
        selected.add(word_list[idx])

    word_idx = {w: i for i, w in enumerate(word_list)}
    res = sorted(
        list(selected),
        key=lambda w: (max(costs[word_idx[w]]), costs[word_idx[w]][0]),
    )[:KEEP]
    return {"words": res, "note": f"pool {len(words)} words, selected {len(res)}"}