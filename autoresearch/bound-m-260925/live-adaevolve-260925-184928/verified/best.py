"""Cyclic-sweep family certifier, top 16 (control b16, campaign seed).

certify(family) returns up to 16 sorting words for the unit base of (a, S).
The unit base v has one zero per nonempty gap. L moves a cursor one cell
right, R one cell left, X swaps the cells under the cursor and its right
neighbor (on the vector: L rotates left, X swaps the first two entries).

Pool: for every target rotation t of the root on the ring, every cyclic
assignment of the interchangeable zeros to the zero slots, and every sweep mode
(L-wise, R-wise, greedy nearest), give each cell a displacement on the universal
cover and sweep, swapping an adjacent pair exactly when the pair must cross;
two zeros never swap (they exchange displacements for free). Each word is
priced by the Lemma 1 affine cost B + sum_j beta_j z_j that the evaluator uses:
B = swaps + sum over segments |net rotation|, beta_j = 2 A_j + sum over
segments |signed crossings of zero block j|, where a segment ends at every X
and A_j counts the X letters that touch block j. The evaluator certifies the
family when some mixture of the returned words has weighted B < T + 1 and every
weighted beta_j <= m - 2. This seed keeps the 16 words with the lowest
(max_j beta_j, B) and leaves the mixture to the evaluator's exact LP.
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


def _lifts(v, t, shift, m, r, zdir=1, zpref='min_z'):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + zdir * i) % r]] = (t + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    if q != 0:
        if zpref == 'min_z':
            order = sorted(range(n), key=lambda p: (1 if v[p] == 0 else 0, -rem[p] if q > 0 else rem[p]))
        elif zpref == 'max_z':
            order = sorted(range(n), key=lambda p: (0 if v[p] == 0 else 1, -rem[p] if q > 0 else rem[p]))
        else:
            order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
        for p in order[:abs(q)]:
            rem[p] -= n if q > 0 else -n
    return rem


import heapq


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

    # Weight configurations for cost-based exploration
    penalty_z_swap = 6 if mode == 'heap_zpen' else 3
    penalty_z_cross = 5 if mode == 'heap_zpen' else 2

    while any(rem) and len(out) < limit:
        if mode == 'greedy':
            for dist in range(n):
                if must_cross((c + dist) % n):
                    out.append('L' * dist)
                    c = (c + dist) % n
                    break
                if must_cross((c - dist) % n):
                    out.append('R' * dist)
                    c = (c - dist) % n
                    break
            else:
                return None
            cross(c)
            continue
        if mode == 'greedy_R':
            for dist in range(n):
                if must_cross((c - dist) % n):
                    out.append('R' * dist)
                    c = (c - dist) % n
                    break
                if must_cross((c + dist) % n):
                    out.append('L' * dist)
                    c = (c + dist) % n
                    break
            else:
                return None
            cross(c)
            continue
        if mode == 'greedy_nz':
            found = False
            for dist in range(n):
                p1 = (c + dist) % n
                if must_cross(p1) and a[p1] and a[(p1 + 1) % n]:
                    out.append('L' * dist)
                    c = p1
                    found = True
                    break
                p2 = (c - dist) % n
                if must_cross(p2) and a[p2] and a[(p2 + 1) % n]:
                    out.append('R' * dist)
                    c = p2
                    found = True
                    break
            if not found:
                for dist in range(n):
                    if must_cross((c + dist) % n):
                        out.append('L' * dist)
                        c = (c + dist) % n
                        break
                    if must_cross((c - dist) % n):
                        out.append('R' * dist)
                        c = (c - dist) % n
                        break
                else:
                    return None
            cross(c)
            continue
        if mode in ('greedy_cost', 'heap_zpen'):
            # Priority queue search over candidate next crossings minimizing zero-cross penalty
            candidates = []
            for x in range(n):
                if must_cross(x):
                    dL = (x - c) % n
                    dR = (c - x) % n
                    is_z_swap = 1 if (a[x] == 0 or a[(x + 1) % n] == 0) else 0
                    zL = sum(1 for step in range(dL) if a[(c + step) % n] == 0)
                    cL = dL + penalty_z_swap * is_z_swap + penalty_z_cross * zL
                    heapq.heappush(candidates, (cL, x, 'L', dL))
                    zR = sum(1 for step in range(dR) if a[(c - step) % n] == 0)
                    cR = dR + penalty_z_swap * is_z_swap + penalty_z_cross * zR
                    heapq.heappush(candidates, (cR, x, 'R', dR))
            if not candidates:
                return None
            best_cost, best_c, best_dir, best_d = heapq.heappop(candidates)
            out.append(best_dir * best_d)
            c = best_c
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
    n, m = len(v), max(v)
    r = n - m
    words = {}
    modes = ('L', 'R', 'greedy', 'greedy_R', 'greedy_nz', 'greedy_cost', 'heap_zpen')
    zdirs = (1, -1) if r > 1 else (1,)
    zprefs = ('min_z', 'max_z', 'default')
    for t in range(n):
        for shift in range(r):
            for zdir in zdirs:
                for zpref in zprefs:
                    rem = _lifts(v, t, shift, m, r, zdir, zpref)
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


def certify(family):
    v = family['unit_base']
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)

    words = pool(v)
    if not words:
        return {'words': []}

    # Vectorize costs: cost_vec = [beta_0, ..., beta_{k-1}, B]
    # Bound vector: [m - 2, ..., m - 2, T]
    # Excess vector: cost_vec - bounds
    word_list = list(words.keys())
    excesses = []
    for w in word_list:
        B, beta = words[w]
        excesses.append([beta[j] - (m - 2) for j in range(k)] + [B - T])

    num_constraints = k + 1
    # Multiplicative weights / Frank-Wolfe greedy selector to find complementary words
    # maintaining a distribution over constraints that identifies bottlenecks
    selected_indices = set()

    # Always seed with the word with minimum max excess
    best_single = min(range(len(word_list)), key=lambda i: max(excesses[i]))
    selected_indices.add(best_single)

    # Also seed with best word for each zero block and B
    for j in range(num_constraints):
        best_j = min(range(len(word_list)), key=lambda i: (excesses[i][j], max(excesses[i])))
        selected_indices.add(best_j)

    # Iterative Frank-Wolfe / subgradient pursuit on minimax excess
    cur_weights = [0.0] * len(word_list)
    cur_weights[best_single] = 1.0

    for step in range(120):
        # Current weighted excess for each constraint
        comb = [sum(cur_weights[i] * excesses[i][c] for i in range(len(word_list)) if cur_weights[i] > 0)
                for c in range(num_constraints)]
        max_val = max(comb)
        # Exponentiated weights over constraints (softmax) to focus on tight/violating constraints
        exps = [pow(2.71828, min(20.0, 2.0 * (comb[c] - max_val))) for c in range(num_constraints)]
        sum_exps = sum(exps)
        dual = [e / sum_exps for e in exps]

        # Find word in pool that minimizes dot(dual, excess)
        best_candidate = min(range(len(word_list)),
                             key=lambda i: sum(dual[c] * excesses[i][c] for c in range(num_constraints)))
        selected_indices.add(best_candidate)

        # Update mixture: step size gamma = 2 / (step + 2)
        gamma = 2.0 / (step + 2)
        for i in range(len(word_list)):
            cur_weights[i] = (1.0 - gamma) * cur_weights[i]
        cur_weights[best_candidate] += gamma

        if len(selected_indices) >= KEEP:
            break

    # If still under KEEP, backfill with lowest max excess
    if len(selected_indices) < KEEP:
        ranked = sorted(range(len(word_list)), key=lambda i: (max(excesses[i]), excesses[i][-1]))
        for i in ranked:
            selected_indices.add(i)
            if len(selected_indices) >= KEEP:
                break

    selected_words = [word_list[i] for i in selected_indices][:KEEP]
    return {'words': selected_words, 'note': 'sweep pool %d words, selected %d LP-aligned words'
            % (len(words), len(selected_words))}
