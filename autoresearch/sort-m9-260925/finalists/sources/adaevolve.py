"""Heuristic LRX sorter (control b): cyclic bubble sweeps with zero blocks as buffers.

The vector is a ring with a moving window: L/R move the window, X swaps the two
ring cells under it. The target is any rotation k of the root on the ring, with
the window finally on label 1. For each k and each cyclic assignment of the
(interchangeable) zeros to the zero slots, every element gets an integer
displacement on the universal cover (shortest way round, adjusted so the sum is
zero). The window then sweeps and swaps an adjacent pair exactly when the pair
must cross on the cover. Two zeros never swap: they exchange displacements for
free, so zero blocks act as buffers. Sweeps run L-wise, R-wise, or greedy to
the nearest pair that must cross. The shortest word over all choices is freely
reduced (LR, RL, XX), replayed, and returned; control (a) is the fallback.
"""


def _replay(v, word):
    a = list(v)
    for ch in word:
        if ch == 'L':
            a.append(a.pop(0))
        elif ch == 'R':
            a.insert(0, a.pop())
        else:
            a[0], a[1] = a[1], a[0]
    return a


def _reduce(word, n):
    tokens = []
    i = 0
    while i < len(word):
        if word[i] == 'X':
            tokens.append('X')
            i += 1
        else:
            rot = 0
            while i < len(word) and word[i] in ('L', 'R'):
                rot += 1 if word[i] == 'L' else -1
                i += 1
            rot %= n
            if rot > n // 2:
                rot -= n
            if rot != 0:
                tokens.append(('L' * rot) if rot > 0 else ('R' * (-rot)))

    changed = True
    while changed:
        changed = False
        new_tokens = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t == 'X':
                if new_tokens and new_tokens[-1] == 'X':
                    new_tokens.pop()
                    changed = True
                    i += 1
                    continue
                new_tokens.append('X')
                i += 1
            else:
                rot = (t.count('L') - t.count('R'))
                j = i + 1
                while j < len(tokens) and tokens[j] != 'X':
                    rot += (tokens[j].count('L') - tokens[j].count('R'))
                    j += 1
                rot %= n
                if rot > n // 2:
                    rot -= n
                if new_tokens and new_tokens[-1] != 'X':
                    prev = new_tokens.pop()
                    rot += (prev.count('L') - prev.count('R'))
                    rot %= n
                    if rot > n // 2:
                        rot -= n
                    changed = True
                if rot != 0:
                    new_tokens.append(('L' * rot) if rot > 0 else ('R' * (-rot)))
                else:
                    changed = True
                i = j
        tokens = new_tokens
    return ''.join(tokens)


try:
    from scipy.optimize import linear_sum_assignment
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def _get_zero_assignments(zeros, zero_targets, n):
    r = len(zeros)
    assignments = []
    for shift in range(r):
        assignments.append([(shift + i) % r for i in range(r)])
        if r > 1:
            assignments.append([(shift - i) % r for i in range(r)])

    if _HAS_SCIPY:
        cost = [[abs(((zero_targets[j] - zeros[i] + n // 2) % n) - n // 2) for j in range(r)] for i in range(r)]
        _, col_ind = linear_sum_assignment(cost)
        assignments.append(list(col_ind))
        # Also try squared cost for minimizing variance of displacements
        cost_sq = [[(((zero_targets[j] - zeros[i] + n // 2) % n) - n // 2) ** 2 for j in range(r)] for i in range(r)]
        _, col_sq = linear_sum_assignment(cost_sq)
        assignments.append(list(col_sq))
    elif r <= 5:
        from itertools import permutations
        best_p, best_c = None, float('inf')
        for p in permutations(range(r)):
            c = sum(abs(((zero_targets[p[i]] - zeros[i] + n // 2) % n) - n // 2) for i in range(r))
            if c < best_c:
                best_c, best_p = c, list(p)
        if best_p is not None:
            assignments.append(best_p)

    seen = set()
    unique = []
    for a in assignments:
        ta = tuple(a)
        if ta not in seen:
            seen.add(ta)
            unique.append(a)
    return unique


def _lifts(v, k, assign, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (k + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (k + m + assign[i]) % n
    base_rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]

    s = sum(base_rem)
    candidates = []
    for q in (s // n, (s + n - 1) // n):
        rem = list(base_rem)
        order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
        for p in order[:abs(q)]:
            rem[p] -= n if q > 0 else -n
        candidates.append(rem)

    candidates.sort(key=lambda c: sum(abs(x) for x in c))
    return candidates[0]


def _sweep(v, rem, k, mode, limit=2000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def free_zero_swaps():
        ch = True
        while ch:
            ch = False
            for x in range(n):
                y = (x + 1) % n
                if a[x] == 0 and a[y] == 0 and rem[x] - rem[y] >= 2:
                    rem[x], rem[y] = rem[y] + 1, rem[x] - 1
                    ch = True

    free_zero_swaps()

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] == 0 and a[y] == 0:
            rem[x], rem[y] = ry + 1, rx - 1
        else:
            out.append('X')
            a[x], a[y] = a[y], a[x]
            rem[x], rem[y] = ry + 1, rx - 1
        free_zero_swaps()

    while any(rem) and len(out) < limit:
        if mode.startswith('potential'):
            crossings = [p for p in range(n) if must_cross(p)]
            if not crossings:
                return None
            best_p, best_score, best_dir, best_dist = None, float('inf'), 'L', 0
            for p in crossings:
                d_L = (p - c) % n
                d_R = (c - p) % n
                if mode == 'potential_L':
                    d_dist, d_char = d_L, 'L'
                elif mode == 'potential_R':
                    d_dist, d_char = d_R, 'R'
                else:
                    if d_L <= d_R:
                        d_dist, d_char = d_L, 'L'
                    else:
                        d_dist, d_char = d_R, 'R'

                swap_cost = 0 if (a[p] == 0 and a[(p + 1) % n] == 0) else 1
                rx, ry = rem[p], rem[(p + 1) % n]
                delta_abs = (abs(ry + 1) + abs(rx - 1)) - (abs(rx) + abs(ry))

                next_min_dist = 0
                if len(crossings) > 1 and 'lookahead' in mode:
                    next_min_dist = min(
                        min((q - p) % n, (p - q) % n) for q in crossings if q != p
                    )

                score = d_dist + swap_cost + 1.2 * delta_abs + 0.5 * next_min_dist
                if score < best_score:
                    best_score = score
                    best_p, best_dir, best_dist = p, d_char, d_dist
            if best_dist:
                out.append(best_dir * best_dist)
            c = best_p
            cross(c)
            continue
        if mode in ('greedy', 'greedy_R'):
            found = False
            for dist in range(n):
                dirs = ((c + dist) % n, 'L', dist) if mode == 'greedy' else ((c - dist) % n, 'R', dist)
                other = ((c - dist) % n, 'R', dist) if mode == 'greedy' else ((c + dist) % n, 'L', dist)
                for pos, d_char, d_dist in (dirs, other):
                    if must_cross(pos):
                        if d_dist:
                            out.append(d_char * d_dist)
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
        if mode == 'L':
            out.append('L')
            c = (c + 1) % n
        elif mode == 'R':
            out.append('R')
            c = (c - 1) % n
        elif mode == 'alt_L':
            step = len(out) // n
            d_ch = 'L' if step % 2 == 0 else 'R'
            out.append(d_ch)
            c = (c + 1) % n if d_ch == 'L' else (c - 1) % n
        elif mode == 'alt_R':
            step = len(out) // n
            d_ch = 'R' if step % 2 == 0 else 'L'
            out.append(d_ch)
            c = (c - 1) % n if d_ch == 'R' else (c + 1) % n
    if any(rem):
        return None
    d = (k - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def _naive(v):
    a = list(v)
    n, m = len(a), max(a)
    key = [x if x else m + 1 for x in a]
    out, c, end = [], 0, n - 1
    while end > 0:
        last = 0
        for i in range(end):
            if key[i] > key[i + 1]:
                k = (i - c) % n
                out.append(('L' * k if k <= n - k else 'R' * (n - k)) + 'X')
                c = i
                key[i], key[i + 1] = key[i + 1], key[i]
                last = i
        end = last
    k = (-c) % n
    out.append('L' * k if k <= n - k else 'R' * (n - k))
    return ''.join(out)


import heapq
import time


def _solve_with_sweeps(v, n, m, r, goal, modes, t_limit=None, t_start=None):
    best = None
    zeros = [p for p in range(n) if v[p] == 0]
    cands = []
    for k in range(n):
        if r > 0:
            zero_targets = [(k + m + i) % n for i in range(r)]
            zero_assignments = _get_zero_assignments(zeros, zero_targets, n)
        else:
            zero_assignments = [[]]
        for assign in zero_assignments:
            rem = _lifts(v, k, assign, m, r) if r else [0] * n
            cands.append((sum(abs(x) for x in rem), k, rem))
    cands.sort(key=lambda item: item[0])

    for _, k, rem in cands:
        if t_limit and t_start and (time.perf_counter() - t_start > t_limit):
            break
        for mode in modes:
            w = _sweep(v, rem, k, mode)
            if w is not None:
                w = _reduce(w, n)
                if (best is None or len(w) < len(best)) and _replay(v, w) == goal:
                    best = w
    return best


def sort_word(v):
    t_start = time.perf_counter()
    v = list(v)
    n, m = len(v), max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    T_budget = m * (m + 1) // 2 + (r - 1) * (m - 2) if r >= 1 else m * (m + 1) // 2
    modes = ('potential', 'potential_L', 'potential_R', 'potential_lookahead', 'greedy', 'greedy_R', 'L', 'R', 'alt_L', 'alt_R')

    best = _solve_with_sweeps(v, n, m, r, goal, modes, t_limit=0.06, t_start=t_start)

    # If the word exceeds budget or is within 2 steps of budget, run branch-and-bound short-horizon search
    if best is None or len(best) >= T_budget - 1:
        # Priority queue search using heapq.heappop on initial steps
        # State tuple: (estimated_cost, depth, current_tuple, prefix)
        fast_modes = ('potential', 'greedy', 'greedy_R', 'alt_L')
        pq = []
        init_tup = tuple(v)
        visited = {init_tup: 0}
        heapq.heappush(pq, (0, 0, init_tup, ""))

        max_depth = 7
        eval_count = 0
        while pq and (time.perf_counter() - t_start < 0.17):
            est_cost, d, cur_state, prefix = heapq.heappop(pq)
            if d > 0:
                eval_count += 1
                # Try completing the sort from this prefix state
                w_suffix = _solve_with_sweeps(list(cur_state), n, m, r, goal, fast_modes, t_limit=0.17, t_start=t_start)
                if w_suffix is not None:
                    candidate = _reduce(prefix + w_suffix, n)
                    if (best is None or len(candidate) < len(best)) and _replay(v, candidate) == goal:
                        best = candidate
                        if len(best) <= T_budget - 2:
                            break

            if d >= max_depth:
                continue

            last_ch = prefix[-1] if prefix else ''
            cur_list = list(cur_state)

            # Generate successors: L, R, X
            transitions = []
            if last_ch != 'R':
                transitions.append(('L', cur_list[1:] + [cur_list[0]]))
            if last_ch != 'L':
                transitions.append(('R', [cur_list[-1]] + cur_list[:-1]))
            if last_ch != 'X':
                swapped = list(cur_list)
                swapped[0], swapped[1] = swapped[1], swapped[0]
                transitions.append(('X', swapped))

            for move, nxt in transitions:
                nxt_tup = tuple(nxt)
                if nxt_tup not in visited or visited[nxt_tup] > d + 1:
                    visited[nxt_tup] = d + 1
                    # Inversion metric for priority estimation
                    inv = 0
                    for i in range(n):
                        for j in range(i + 1, n):
                            vi, vj = nxt[i], nxt[j]
                            if vi > 0 and vj > 0 and vi > vj:
                                inv += 1
                    h_score = d + 1 + inv * 0.8
                    heapq.heappush(pq, (h_score, d + 1, nxt_tup, prefix + move))

    return best if best is not None else _naive(v)
