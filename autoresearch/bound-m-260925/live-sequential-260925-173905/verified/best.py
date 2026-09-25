"""LRX sorting word generator and LP certifier for family unit base."""

import fractions

KEEP = 32


def _reduce(w):
    out = []
    for ch in w:
        if out and ((ch == 'L' and out[-1] == 'R') or
                    (ch == 'R' and out[-1] == 'L') or
                    (ch == 'X' and out[-1] == 'X')):
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
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    if bias == 0:
        order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    elif bias == 1:
        order = sorted(range(n), key=lambda p: (rem[p], p), reverse=q > 0)
    elif bias == -1:
        order = sorted(range(n), key=lambda p: (-rem[p], p), reverse=q > 0)
    elif bias == 2:
        order = sorted(range(n), key=lambda p: (v[p] == 0, rem[p]), reverse=q > 0)
    elif bias == -2:
        order = sorted(range(n), key=lambda p: (v[p] != 0, rem[p]), reverse=q > 0)
    elif bias == 3:
        order = sorted(range(n), key=lambda p: (rem[p], -p), reverse=q > 0)
    elif bias == 5:
        order = sorted(range(n), key=lambda p: (rem[p] % 2, rem[p]), reverse=q > 0)
    elif bias == -5:
        order = sorted(range(n), key=lambda p: (rem[p] % 2, -rem[p]), reverse=q > 0)
    else:
        order = sorted(range(n), key=lambda p: abs(rem[p]), reverse=q > 0)
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
    pdir = 1
    while any(rem) and steps < limit:
        steps += 1
        if mode == 'greedy':
            found = False
            for dist in range(n):
                p1 = (c + dist) % n
                p2 = (c - dist) % n
                if must_cross(p1):
                    out.append('L' * dist)
                    c = p1
                    found = True
                    break
                if must_cross(p2):
                    out.append('R' * dist)
                    c = p2
                    found = True
                    break
            if not found:
                return None
            cross(c)
            continue

        if mode == 'pingpong':
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            ahead = False
            for step in range(1, n // 2 + 1):
                chk = (c + pdir * step) % n
                if must_cross(chk):
                    ahead = True
                    break
            if not ahead:
                pdir = -pdir
            c = (c + pdir) % n
            out.append('L' if pdir == 1 else 'R')
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
    n = len(v)
    k = sum(1 for x in v if x == 0)
    a = []
    j = 0
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


def _insertion_sort_words(v):
    n = len(v)
    m = max(v)
    out_words = []

    for t_final in range(n):
        for reverse in (False, True):
            for route_dir in (1, -1, 0):
                a = list(v)
                c = 0
                ops = []

                def goto(target):
                    nonlocal c
                    d = (target - c) % n
                    if d <= n - d:
                        ops.append('L' * d)
                    else:
                        ops.append('R' * (n - d))
                    c = target

                def swap_at(idx):
                    goto(idx)
                    ops.append('X')
                    a[c], a[(c + 1) % n] = a[(c + 1) % n], a[c]

                valid = True
                order = list(range(m, 0, -1)) if reverse else list(range(1, m + 1))
                for val in order:
                    curr_pos = a.index(val)
                    desired_pos = (t_final + val - 1) % n

                    while curr_pos != desired_pos:
                        if route_dir == 1:
                            step = 1
                        elif route_dir == -1:
                            step = -1
                        else:
                            step = 1 if (desired_pos - curr_pos) % n <= n // 2 else -1
                        next_pos = (curr_pos + step) % n
                        sw_idx = curr_pos if step == 1 else next_pos
                        if a[sw_idx] == 0 and a[(sw_idx + 1) % n] == 0:
                            valid = False
                            break
                        swap_at(sw_idx)
                        curr_pos = next_pos
                    if not valid:
                        break

                if valid:
                    goto(t_final)
                    w = ''.join(ops)
                    out_words.append(w)
    return out_words


def _bubble_sort_words(v):
    n = len(v)
    m = max(v)
    out_words = []

    for t_final in range(n):
        target_positions = {}
        for p in range(n):
            if v[p] > 0:
                target_positions[v[p]] = (t_final + v[p] - 1) % n

        for sweep_dir in ('L', 'R'):
            a = list(v)
            c = 0
            ops = []

            def goto(target):
                nonlocal c
                d = (target - c) % n
                if d <= n - d:
                    ops.append('L' * d)
                else:
                    ops.append('R' * (n - d))
                c = target

            def swap_at(idx):
                goto(idx)
                ops.append('X')
                a[c], a[(c + 1) % n] = a[(c + 1) % n], a[c]

            valid = True
            for _ in range(n * 2):
                swapped = False
                scan_range = range(n) if sweep_dir == 'L' else range(n - 1, -1, -1)
                for i in scan_range:
                    j = (i + 1) % n
                    xi, xj = a[i], a[j]
                    if xi == 0 and xj == 0:
                        continue
                    if xi > 0 and xj > 0:
                        des_i = target_positions[xi]
                        des_j = target_positions[xj]
                        inv = ((des_i - t_final) % n) > ((des_j - t_final) % n)
                    elif xi > 0 and xj == 0:
                        des_i = (target_positions[xi] - t_final) % n
                        inv = des_i >= m
                    elif xi == 0 and xj > 0:
                        des_j = (target_positions[xj] - t_final) % n
                        inv = des_j < m
                    else:
                        inv = False

                    if inv:
                        if xi == 0 and xj == 0:
                            valid = False
                            break
                        swap_at(i)
                        swapped = True
                if not swapped or not valid:
                    break

            if valid:
                fin = a[t_final:] + a[:t_final]
                if fin[:m] == list(range(1, m + 1)):
                    goto(t_final)
                    out_words.append(''.join(ops))
    return out_words


def _solve_gap_lp(word_data, s_max, T, max_iter=300):
    if not word_data:
        return float('inf'), []
    k = len(word_data[0][1])
    p = len(word_data)
    w = [1.0 / p] * p
    best_g = float('inf')
    best_w = list(w)

    T_target = T + 0.999
    for it in range(max_iter):
        B_val = sum(w[i] * word_data[i][0] for i in range(p)) - T_target
        slopes = [sum(w[i] * word_data[i][1][j] for i in range(p)) - s_max for j in range(k)]
        g = max([B_val] + slopes)
        if g < best_g:
            best_g = g
            best_w = list(w)
        if g <= 0:
            break
        if B_val >= max(slopes):
            subg = [word_data[i][0] for i in range(p)]
        else:
            j_star = max(range(k), key=lambda j: slopes[j])
            subg = [word_data[i][1][j_star] for i in range(p)]
        i_best = min(range(p), key=lambda i: subg[i])
        step = 2.0 / (it + 3)
        for i in range(p):
            w[i] = (1.0 - step) * w[i] + (step if i == i_best else 0.0)

    return best_g, best_w


def _select_optimal_pool(words, target_count, m, T):
    if len(words) <= target_count:
        return list(words.keys())

    s_max = m - 2
    item_list = []
    w_list = list(words.keys())
    for w in w_list:
        b, beta = words[w]
        viol = sum(max(0, x - s_max) for x in beta)
        b_excess = max(0, b - T)
        max_b = max(beta)
        item_list.append((viol, b_excess, max_b, b, w, beta))

    k = len(item_list[0][5])
    selected_indices = set()

    item_list_sorted = sorted(
        range(len(item_list)),
        key=lambda i: (item_list[i][0], item_list[i][2], item_list[i][1], item_list[i][3])
    )

    for idx in item_list_sorted[:min(4, len(item_list))]:
        selected_indices.add(idx)

    for j in range(k):
        sorted_by_j = sorted(
            range(len(item_list)),
            key=lambda i: (item_list[i][5][j], item_list[i][0], item_list[i][3])
        )
        for idx in sorted_by_j[:2]:
            selected_indices.add(idx)

    sorted_by_b = sorted(
        range(len(item_list)),
        key=lambda i: (item_list[i][3], item_list[i][0])
    )
    for idx in sorted_by_b[:2]:
        selected_indices.add(idx)

    curr = list(selected_indices)
    curr_data = [(item_list[idx][3], item_list[idx][5]) for idx in curr]
    curr_g, _ = _solve_gap_lp(curr_data, s_max, T, max_iter=80)

    candidates = [i for i in item_list_sorted if i not in selected_indices]
    while len(curr) < target_count and candidates:
        if curr_g <= 0:
            for cand in candidates:
                if len(curr) >= target_count:
                    break
                curr.append(cand)
            break

        best_cand = None
        best_cand_g = curr_g
        eval_cands = candidates[:min(60, len(candidates))]
        for cand in eval_cands:
            trial = curr + [cand]
            trial_data = [(item_list[idx][3], item_list[idx][5]) for idx in trial]
            g, _ = _solve_gap_lp(trial_data, s_max, T, max_iter=90)
            if g < best_cand_g:
                best_cand_g = g
                best_cand = cand
                if g <= 0:
                    break

        if best_cand is None:
            best_cand = candidates[0]
            best_cand_g = curr_g

        curr.append(best_cand)
        selected_indices.add(best_cand)
        candidates.remove(best_cand)
        curr_g = best_cand_g

    return [item_list[idx][4] for idx in curr[:target_count]]


def certify(family):
    v = family['unit_base']
    n = len(v)
    m = max(v)
    r = n - m
    T = m * (m + 1) // 2 + (r - 1) * (m - 2)

    words = {}

    def add_word(w):
        if w is None or len(w) > 4000:
            return
        w = _reduce(w)
        if w not in words and len(w) <= 4000:
            cost = price(v, w)
            if cost is not None:
                words[w] = cost

    modes = ('L', 'R', 'greedy', 'pingpong')

    for t in range(n):
        for shift in range(r):
            for bias in (0, 1, -1, 2, -2, 3, -3, 4, 5, -5):
                rem = _lifts(v, t, shift, m, r, bias=bias)
                for mode in modes:
                    w = _sweep(v, rem, t, mode)
                    add_word(w)

    for w in _insertion_sort_words(v):
        add_word(w)

    for w in _bubble_sort_words(v):
        add_word(w)

    chosen = _select_optimal_pool(words, KEEP, m, T)
    return {'words': chosen}
