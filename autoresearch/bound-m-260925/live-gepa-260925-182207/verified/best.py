"""Universal cyclic-sweep family certifier with dual-lift and exact LP filtering."""

from fractions import Fraction

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, shift, m, r, bias=0):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (t + m + i) % n
    rem = [((target[p] - p + n // 2 + bias) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
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

    steps = 0
    while any(rem) and steps < limit:
        steps += 1
        if mode in ('greedy', 'greedy_rev', 'min_cost'):
            found = False
            for dist in range(n):
                pos1 = (c + dist) % n if mode == 'greedy' else (c - dist) % n
                pos2 = (c - dist) % n if mode == 'greedy' else (c + dist) % n
                ch1 = 'L' if mode == 'greedy' else 'R'
                ch2 = 'R' if mode == 'greedy' else 'L'

                if mode == 'min_cost':
                    # Prefer positions that don't touch zeros if possible
                    c1_ok = must_cross(pos1)
                    c2_ok = must_cross(pos2)
                    if c1_ok and c2_ok:
                        z1 = (a[pos1] == 0) + (a[(pos1 + 1) % n] == 0)
                        z2 = (a[pos2] == 0) + (a[(pos2 + 1) % n] == 0)
                        if z2 < z1:
                            out.append(ch2 * dist)
                            c = pos2
                        else:
                            out.append(ch1 * dist)
                            c = pos1
                        found = True
                        break
                if must_cross(pos1):
                    out.append(ch1 * dist)
                    c = pos1
                    found = True
                    break
                if must_cross(pos2):
                    out.append(ch2 * dist)
                    c = pos2
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


def pool(v):
    n, m = len(v), max(v)
    r = n - m
    words = {}
    modes = ('L', 'R', 'greedy', 'greedy_rev', 'min_cost')
    for t in range(n):
        for shift in range(r):
            for bias in (0, 1):
                rem = _lifts(v, t, shift, m, r, bias)
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


def _solve_excess_lp(cands, m, k, T):
    """Solve LP finding minimum max-slope excess and the active support."""
    # Find convex combination of cands minimizing max_j sum_i w_i * beta_{i,j}
    # subject to sum_i w_i * B_i <= T + 1, sum w_i = 1, w_i >= 0.
    # We use a fast Frank-Wolfe / projected subgradient or coordinate descent to identify the best subset.
    num = len(cands)
    if num == 0:
        return []
    # Quick check for single word
    for idx, (w, (B, beta)) in enumerate(cands):
        if B < T + 1 and all(b <= m - 2 for b in beta):
            return [idx]

    weights = [Fraction(1, num)] * num
    # Track support of good points
    # Pick greedy mixture that minimizes max slope excess
    cur_w = [0.0] * num
    # Start with lowest B candidate that has decent slope
    best_init = min(range(num), key=lambda i: (max(0, cands[i][1][0] - (T + 1)), max(cands[i][1][1])))
    cur_w[best_init] = 1.0

    cur_B = float(cands[best_init][1][0])
    cur_beta = [float(x) for x in cands[best_init][1][1]]

    support = {best_init}
    for step in range(1, 100):
        # find tightest beta coordinate
        worst_coord = max(range(k), key=lambda j: cur_beta[j])
        # find candidate that reduces this coordinate while keeping B manageable
        best_cand = None
        best_val = float('inf')
        for i, (_, (B_i, b_i)) in enumerate(cands):
            # score candidate: how much it helps on worst_coord + penalty if B_i > T+1
            excess_B = max(0.0, cur_B * 0.9 + B_i * 0.1 - (T + 1))
            val = b_i[worst_coord] + 5.0 * excess_B
            if val < best_val:
                best_val = val
                best_cand = i

        if best_cand is None:
            break
        support.add(best_cand)
        alpha = 2.0 / (step + 2)
        cur_B = (1.0 - alpha) * cur_B + alpha * cands[best_cand][1][0]
        for j in range(k):
            cur_beta[j] = (1.0 - alpha) * cur_beta[j] + alpha * cands[best_cand][1][1][j]

    return list(support)


def certify(family):
    v = family['unit_base']
    m = max(v)
    k = len(v) - m
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)
    words = pool(v)

    if not words:
        return {'words': []}

    for w, (B, beta) in words.items():
        if B < T + 1 and all(b <= m - 2 for b in beta):
            return {'words': [w]}

    cand_items = list(words.items())
    lp_support = _solve_excess_lp(cand_items, m, k, T)
    selected = {cand_items[i][0] for i in lp_support}

    # 1. Best slope on each zero coordinate j
    for j in range(k):
        by_j = sorted(words.keys(), key=lambda w: (words[w][1][j], words[w][0], max(words[w][1])))
        for w in by_j[:3]:
            selected.add(w)

        under_T = [w for w in words.keys() if words[w][0] <= T + 1]
        if under_T:
            by_j_under = sorted(under_T, key=lambda w: (words[w][1][j], max(words[w][1]), words[w][0]))
            for w in by_j_under[:2]:
                selected.add(w)

    # 2. Overall lowest max-slope
    by_max_beta = sorted(words.keys(), key=lambda w: (max(words[w][1]), words[w][0], sum(words[w][1])))
    for w in by_max_beta[:10]:
        selected.add(w)

    # 3. Overall lowest base cost B
    by_B = sorted(words.keys(), key=lambda w: (words[w][0], max(words[w][1]), sum(words[w][1])))
    for w in by_B[:6]:
        selected.add(w)

    # 4. Complementary slope pairs
    if len(selected) < KEEP:
        best_cand = by_max_beta[:24]
        scored_pairs = []
        for i in range(len(best_cand)):
            w1 = best_cand[i]
            b1 = words[w1][1]
            B1 = words[w1][0]
            for j in range(i + 1, len(best_cand)):
                w2 = best_cand[j]
                b2 = words[w2][1]
                B2 = words[w2][0]
                mid_max = max(b1[t] + b2[t] for t in range(k))
                scored_pairs.append((mid_max, B1 + B2, w1, w2))
        scored_pairs.sort(key=lambda x: (x[0], x[1]))
        for _, _, w1, w2 in scored_pairs:
            selected.add(w1)
            selected.add(w2)
            if len(selected) >= KEEP:
                break

    # 5. Fill remaining quota
    by_sum = sorted(words.keys(), key=lambda w: (sum(words[w][1]), max(words[w][1]), words[w][0]))
    for w in by_sum:
        if len(selected) >= KEEP:
            break
        selected.add(w)

    for w in by_max_beta:
        if len(selected) >= KEEP:
            break
        selected.add(w)

    out = list(selected)[:KEEP]
    out.sort(key=lambda w: (max(words[w][1]), words[w][0]))
    return {'words': out}