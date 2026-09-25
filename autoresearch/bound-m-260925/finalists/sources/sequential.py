"""LRX family certifier with zero-avoidance sweeps and target-slope optimization."""


def _reduce(w):
    out = []
    for c in w:
        if out and out[-1] + c in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(c)
    return ''.join(out)


def _lifts(v, t, shift, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (t + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
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

    steps = 0
    max_steps = 15000
    while any(rem) and len(out) < limit and steps < max_steps:
        steps += 1
        if mode in ('L', 'R'):
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            out.append(mode)
            c = (c + (1 if mode == 'L' else -1)) % n
            continue

        cands = []
        for dist in range(n):
            p1 = (c + dist) % n
            p2 = (c - dist) % n
            if must_cross(p1):
                cands.append(('L', dist, p1))
            if dist > 0 and must_cross(p2):
                cands.append(('R', dist, p2))
            if cands:
                break

        if not cands:
            return None

        if len(cands) == 1:
            direction, dist, p = cands[0]
        else:
            (d1, dist1, p1), (d2, dist2, p2) = cands[0], cands[1]
            z1 = (a[p1] <= 0) + (a[(p1 + 1) % n] <= 0)
            z2 = (a[p2] <= 0) + (a[(p2 + 1) % n] <= 0)

            if mode.startswith('target_'):
                tgt_j = int(mode.split('_')[1])
                z_tgt1 = (a[p1] == -(tgt_j + 1)) or (a[(p1 + 1) % n] == -(tgt_j + 1))
                z_tgt2 = (a[p2] == -(tgt_j + 1)) or (a[(p2 + 1) % n] == -(tgt_j + 1))
                if z_tgt1 != z_tgt2:
                    direction, dist, p = (d1, dist1, p1) if not z_tgt1 else (d2, dist2, p2)
                elif z1 != z2:
                    direction, dist, p = (d1, dist1, p1) if z1 < z2 else (d2, dist2, p2)
                else:
                    direction, dist, p = (d1, dist1, p1) if abs(rem[p1]) >= abs(rem[p2]) else (d2, dist2, p2)
            elif mode.startswith('spartarget_'):
                tgt_j = int(mode.split('_')[1])
                z_tgt1 = (a[p1] == -(tgt_j + 1)) or (a[(p1 + 1) % n] == -(tgt_j + 1))
                z_tgt2 = (a[p2] == -(tgt_j + 1)) or (a[(p2 + 1) % n] == -(tgt_j + 1))
                if z_tgt1 != z_tgt2:
                    direction, dist, p = (d1, dist1, p1) if not z_tgt1 else (d2, dist2, p2)
                else:
                    direction, dist, p = (d1, dist1, p1) if rem[p1] >= rem[p2] else (d2, dist2, p2)
            elif mode == 'cw_pref':
                direction, dist, p = d1, dist1, p1
            elif mode == 'ccw_pref':
                direction, dist, p = d2, dist2, p2
            elif mode == 'greedy':
                direction, dist, p = d1, dist1, p1
            elif mode == 'greedy_rev':
                direction, dist, p = d2, dist2, p2
            elif mode == 'avoid_zeros':
                if (z1 == 0) != (z2 == 0):
                    direction, dist, p = (d1, dist1, p1) if z1 == 0 else (d2, dist2, p2)
                elif z1 != z2:
                    direction, dist, p = (d1, dist1, p1) if z1 < z2 else (d2, dist2, p2)
                else:
                    direction, dist, p = d1, dist1, p1
            elif mode == 'heavy_avoid':
                if z1 != z2:
                    direction, dist, p = (d1, dist1, p1) if z1 < z2 else (d2, dist2, p2)
                else:
                    direction, dist, p = (d1, dist1, p1) if abs(rem[p1]) >= abs(rem[p2]) else (d2, dist2, p2)
            elif mode == 'slope_bias':
                score1 = z1 * 6 - abs(rem[p1])
                score2 = z2 * 6 - abs(rem[p2])
                direction, dist, p = (d1, dist1, p1) if score1 <= score2 else (d2, dist2, p2)
            elif mode == 'zero_bias':
                score1 = (z1 * 4) - abs(rem[p1])
                score2 = (z2 * 4) - abs(rem[p2])
                direction, dist, p = (d1, dist1, p1) if score1 <= score2 else (d2, dist2, p2)
            elif mode == 'balanced':
                direction, dist, p = (d1, dist1, p1) if rem[p1] >= rem[p2] else (d2, dist2, p2)
            else:
                if z1 != z2:
                    direction, dist, p = (d1, dist1, p1) if z1 < z2 else (d2, dist2, p2)
                else:
                    direction, dist, p = d1, dist1, p1

        out.append(direction * dist)
        c = p
        cross(c)

    if any(rem):
        return None
    d = (t - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def _penalty_sweep(v, rem, t, penalty_weights, rot_cost_mult=0.7, limit=4000):
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
    max_steps = 15000
    while any(rem) and len(out) < limit and steps < max_steps:
        steps += 1
        cands = [p for p in range(n) if must_cross(p)]
        if not cands:
            return None

        best_cand = None
        best_cost = 1e9

        for p in cands:
            dL = (p - c) % n
            dR = (c - p) % n

            rot_pL = 0
            for step in range(dL):
                pos = (c + step) % n
                val = a[pos]
                if val < 0:
                    rot_pL += penalty_weights[-val - 1]

            rot_pR = 0
            for step in range(dR):
                pos = (c - step) % n
                val = a[pos]
                if val < 0:
                    rot_pR += penalty_weights[-val - 1]

            p_next = (p + 1) % n
            x_pen = 0
            if a[p] < 0:
                x_pen += 2.0 * penalty_weights[-a[p] - 1]
            if a[p_next] < 0:
                x_pen += 2.0 * penalty_weights[-a[p_next] - 1]

            eff_rem = abs(rem[p] - rem[p_next])

            costL = dL * rot_cost_mult + rot_pL + x_pen - 0.2 * eff_rem
            costR = dR * rot_cost_mult + rot_pR + x_pen - 0.2 * eff_rem

            if costL < best_cost:
                best_cost = costL
                best_cand = ('L', dL, p)
            if costR < best_cost:
                best_cost = costR
                best_cand = ('R', dR, p)

        direction, dist, p = best_cand
        out.append(direction * dist)
        c = p
        cross(c)

    if any(rem):
        return None
    d = (t - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def price(v, word):
    n = len(v)
    k = sum(1 for x in v if x == 0)
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

    base_modes = [
        'L', 'R', 'greedy', 'greedy_rev', 'min_slope', 'avoid_zeros',
        'zero_bias', 'cw_pref', 'ccw_pref', 'heavy_avoid', 'slope_bias', 'balanced'
    ]
    for j in range(r):
        base_modes.append(f'target_{j}')
        base_modes.append(f'spartarget_{j}')

    v_tagged = []
    j_cnt = 0
    for x in v:
        if x == 0:
            j_cnt += 1
            v_tagged.append(-j_cnt)
        else:
            v_tagged.append(x)

    def add_word_candidate(w):
        if w is None:
            return
        w = _reduce(w)
        if len(w) <= 4000 and w not in words:
            cost = price(v, w)
            if cost is not None:
                words[w] = cost

    for t in range(n):
        for shift in range(r):
            rem = _lifts(v, t, shift, m, r)
            for mode in base_modes:
                add_word_candidate(_sweep(v_tagged, rem, t, mode))

    penalty_sets = []
    for j in range(r):
        pw = [0.2] * r
        pw[j] = 5.0
        penalty_sets.append((pw, 0.7))
        pw2 = [0.05] * r
        pw2[j] = 15.0
        penalty_sets.append((pw2, 0.5))
        if r > 1:
            pw3 = [0.1] * r
            pw3[j] = 8.0
            pw3[(j + 1) % r] = 8.0
            penalty_sets.append((pw3, 0.7))
        if r == 2:
            pw4 = [0.0, 0.0]
            pw4[j] = 25.0
            penalty_sets.append((pw4, 0.3))

    t_candidates = list(range(n)) if n <= 15 else list(range(0, n, 2))
    for pw, r_mult in penalty_sets:
        for t in t_candidates:
            for shift in range(r):
                rem = _lifts(v, t, shift, m, r)
                add_word_candidate(_penalty_sweep(v_tagged, rem, t, pw, r_mult))

    return words


def _eval_excess(words_costs, T, s_target, num_steps=400):
    N = len(words_costs)
    if N == 0:
        return 999.0, []
    w_vec = [1.0 / N] * N
    B_list = [c[0] for c in words_costs]
    k = len(words_costs[0][1])
    beta_list = [c[1] for c in words_costs]

    best_excess = 999.0
    best_w = list(w_vec)
    for it in range(num_steps):
        cur_B = sum(w_vec[i] * B_list[i] for i in range(N))
        cur_beta = [sum(w_vec[i] * beta_list[i][j] for i in range(N)) for j in range(k)]
        excesses = [cur_B - (T + 0.999)] + [cur_beta[j] - s_target for j in range(k)]
        max_e = max(excesses)
        if max_e < best_excess:
            best_excess = max_e
            best_w = list(w_vec)
        if max_e <= 0:
            break
        arg_m = excesses.index(max_e)
        if arg_m == 0:
            best_i = min(range(N), key=lambda i: (B_list[i], max(beta_list[i])))
        else:
            j_tight = arg_m - 1
            best_i = min(range(N), key=lambda i: (beta_list[i][j_tight], B_list[i]))
        lr = 2.0 / (it + 3)
        for i in range(N):
            w_vec[i] = (1.0 - lr) * w_vec[i] + (lr if i == best_i else 0.0)

    return best_excess, best_w


def select_best(words, m, k):
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)
    s_limit = m - 2
    if not words:
        return []

    word_items = list(words.items())

    def base_score(cost):
        B, beta = cost
        max_s = max(beta) if beta else 0
        b_excess = max(0, B - (T + 1))
        s_excess = max(0, max_s - s_limit)
        return (max(s_excess, b_excess), s_excess, b_excess, max_s, B)

    word_items.sort(key=lambda item: base_score(item[1]))

    chosen = []
    chosen_set = set()

    def add_word(w):
        if w not in chosen_set and len(chosen) < 32:
            chosen.append(w)
            chosen_set.add(w)

    for w, _ in word_items[:6]:
        add_word(w)

    for j in range(k):
        sorted_j = sorted(word_items, key=lambda item: (item[1][1][j], item[1][0]))
        for w, _ in sorted_j[:4]:
            add_word(w)

    for j1 in range(k):
        for j2 in range(j1 + 1, k):
            sorted_pair = sorted(word_items, key=lambda item: (item[1][1][j1] + item[1][1][j2], item[1][0]))
            for w, _ in sorted_pair[:2]:
                add_word(w)

    by_B = sorted(word_items, key=lambda item: (item[1][0], max(item[1][1])))
    for w, _ in by_B[:6]:
        add_word(w)

    while len(chosen) < 32 and len(chosen) < len(word_items):
        cur_costs = [words[w] for w in chosen]
        cur_excess, w_weights = _eval_excess(cur_costs, T, s_limit)
        if cur_excess <= 0:
            break

        cur_B = sum(w_weights[i] * cur_costs[i][0] for i in range(len(chosen)))
        cur_beta = [sum(w_weights[i] * cur_costs[i][1][j] for i in range(len(chosen))) for j in range(k)]
        excesses = [cur_B - (T + 1)] + [cur_beta[j] - s_limit for j in range(k)]
        tight_idx = excesses.index(max(excesses))

        if tight_idx == 0:
            best_cand = min(
                (item for item in word_items if item[0] not in chosen_set),
                key=lambda item: (item[1][0], max(item[1][1])),
                default=None,
            )
        else:
            j_t = tight_idx - 1
            best_cand = min(
                (item for item in word_items if item[0] not in chosen_set),
                key=lambda item: (item[1][1][j_t], item[1][0]),
                default=None,
            )

        if best_cand is None:
            break
        add_word(best_cand[0])

    for w, _ in word_items:
        if len(chosen) >= 32:
            break
        add_word(w)

    return chosen[:32]


def certify(family):
    v = family['unit_base']
    m = max(v)
    k = sum(1 for x in v if x == 0)
    w_pool = pool(v)
    chosen = select_best(w_pool, m, k)
    return {'words': chosen, 'note': f'pool {len(w_pool)}, selected {len(chosen)}'}
