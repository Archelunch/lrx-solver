"""Uniform constructive LRX sorter using multi-start cyclic sweeps and tie-breaking variations."""


def _reduce(w):
    out = []
    for c in w:
        if out and ((out[-1] == 'L' and c == 'R') or
                    (out[-1] == 'R' and c == 'L') or
                    (out[-1] == 'X' and c == 'X')):
            out.pop()
        else:
            out.append(c)
    return ''.join(out)


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


def _get_lifts(v, k, shift, m, r, center_bias=0):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (k + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (k + m + i) % n

    rem = [((target[p] - p + n // 2 + center_bias) % n) - (n // 2 + center_bias) for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _run_sweep(v, rem, k, mode, limit=400):
    n = len(v)
    a, rem = list(v), list(rem)
    out = []
    c = 0

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] != 0 or a[y] != 0:
            out.append('X')
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    steps = 0
    while any(rem) and len(out) < limit:
        steps += 1
        if steps > 900:
            return None

        if mode == 'greedy':
            found = False
            for dist in range(n):
                p1 = (c + dist) % n
                if rem[p1] - rem[(p1 + 1) % n] >= 2:
                    if dist > 0:
                        out.append('L' * dist)
                    c = p1
                    found = True
                    break
                p2 = (c - dist) % n
                if rem[p2] - rem[(p2 + 1) % n] >= 2:
                    if dist > 0:
                        out.append('R' * dist)
                    c = p2
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == 'greedy_rev':
            found = False
            for dist in range(n):
                p2 = (c - dist) % n
                if rem[p2] - rem[(p2 + 1) % n] >= 2:
                    if dist > 0:
                        out.append('R' * dist)
                    c = p2
                    found = True
                    break
                p1 = (c + dist) % n
                if rem[p1] - rem[(p1 + 1) % n] >= 2:
                    if dist > 0:
                        out.append('L' * dist)
                    c = p1
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == 'greedy_tie_dist':
            found = False
            for dist in range(n):
                dl = dist
                dr = dist
                p1 = (c + dl) % n
                p2 = (c - dr) % n
                c1 = rem[p1] - rem[(p1 + 1) % n] >= 2
                c2 = rem[p2] - rem[(p2 + 1) % n] >= 2
                if c1 and c2:
                    if (rem[p1] - rem[(p1 + 1) % n]) >= (rem[p2] - rem[(p2 + 1) % n]):
                        if dl > 0:
                            out.append('L' * dl)
                        c = p1
                    else:
                        if dr > 0:
                            out.append('R' * dr)
                        c = p2
                    found = True
                    break
                elif c1:
                    if dl > 0:
                        out.append('L' * dl)
                    c = p1
                    found = True
                    break
                elif c2:
                    if dr > 0:
                        out.append('R' * dr)
                    c = p2
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == 'greedy_tie_dist_rev':
            found = False
            for dist in range(n):
                dl = dist
                dr = dist
                p1 = (c + dl) % n
                p2 = (c - dr) % n
                c1 = rem[p1] - rem[(p1 + 1) % n] >= 2
                c2 = rem[p2] - rem[(p2 + 1) % n] >= 2
                if c1 and c2:
                    if (rem[p2] - rem[(p2 + 1) % n]) >= (rem[p1] - rem[(p1 + 1) % n]):
                        if dr > 0:
                            out.append('R' * dr)
                        c = p2
                    else:
                        if dl > 0:
                            out.append('L' * dl)
                        c = p1
                    found = True
                    break
                elif c2:
                    if dr > 0:
                        out.append('R' * dr)
                    c = p2
                    found = True
                    break
                elif c1:
                    if dl > 0:
                        out.append('L' * dl)
                    c = p1
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == 'greedy_max':
            best_diff = 1
            best_p = -1
            best_dist = 1000
            for p in range(n):
                diff = rem[p] - rem[(p + 1) % n]
                if diff >= 2:
                    dl = (p - c) % n
                    dr = (c - p) % n
                    d = min(dl, dr)
                    if diff > best_diff or (diff == best_diff and d < best_dist):
                        best_diff = diff
                        best_dist = d
                        best_p = p
            if best_p == -1:
                return None
            dl = (best_p - c) % n
            dr = (c - best_p) % n
            if dl <= dr:
                out.append('L' * dl)
            else:
                out.append('R' * dr)
            c = best_p
            cross(c)
        elif mode.startswith('greedy_cost'):
            weight = 4 if '4' in mode else (2 if '2' in mode else (5 if '5' in mode else (1.5 if '15' in mode else 3)))
            best_score = -1e9
            best_p = -1
            best_dir = 'L'
            best_d = 0
            for p in range(n):
                diff = rem[p] - rem[(p + 1) % n]
                if diff >= 2:
                    dl = (p - c) % n
                    dr = (c - p) % n
                    d = min(dl, dr)
                    score = diff * weight - d
                    if score > best_score:
                        best_score = score
                        best_p = p
                        best_d = d
                        best_dir = 'L' if dl <= dr else 'R'
            if best_p == -1:
                return None
            if best_d > 0:
                out.append(best_dir * best_d)
            c = best_p
            cross(c)
        elif mode == 'greedy_cost_rev':
            weight = 3
            best_score = -1e9
            best_p = -1
            best_dir = 'R'
            best_d = 0
            for p in range(n):
                diff = rem[p] - rem[(p + 1) % n]
                if diff >= 2:
                    dl = (p - c) % n
                    dr = (c - p) % n
                    d = min(dl, dr)
                    score = diff * weight - d
                    if score > best_score:
                        best_score = score
                        best_p = p
                        best_d = d
                        best_dir = 'R' if dr <= dl else 'L'
            if best_p == -1:
                return None
            if best_d > 0:
                out.append(best_dir * best_d)
            c = best_p
            cross(c)
        else:
            if rem[c] - rem[(c + 1) % n] >= 2:
                cross(c)
                if not any(rem):
                    break
            if mode == 'L':
                out.append('L')
                c = (c + 1) % n
            elif mode == 'R':
                out.append('R')
                c = (c - 1) % n
            elif mode == 'LR':
                if c == n - 1:
                    out.append('R')
                    c = n - 2
                else:
                    out.append('L')
                    c += 1
            elif mode == 'RL':
                if c == 0:
                    out.append('L')
                    c = 1
                else:
                    out.append('R')
                    c -= 1

    if any(rem):
        return None
    d = (k - c) % n
    if d <= n - d:
        out.append('L' * d)
    else:
        out.append('R' * (n - d))
    return ''.join(out)


def _bubble_sort(v, target_perm, strategy='min'):
    n = len(v)
    pos = {val: i for i, val in enumerate(target_perm)}
    arr = [pos[x] for x in v]
    c = 0
    out = []
    while True:
        invs = []
        for i in range(n - 1):
            if arr[i] > arr[i + 1]:
                dl = (i - c) % n
                dr = (c - i) % n
                d = min(dl, dr)
                diff = arr[i] - arr[i + 1]
                invs.append((d, dl <= dr, i, diff))
        if not invs:
            break
        if strategy == 'min':
            invs.sort(key=lambda t: (t[0], -t[3]))
        elif strategy == 'max_diff':
            invs.sort(key=lambda t: (-t[3], t[0]))
        else:
            invs.sort(key=lambda t: (t[0] - t[3] * 2))
        d, go_left, i, _ = invs[0]
        if d > 0:
            out.append(('L' if go_left else 'R') * d)
        out.append('X')
        c = i
        arr[i], arr[i + 1] = arr[i + 1], arr[i]
    d = (-c) % n
    if d <= n - d:
        out.append('L' * d)
    else:
        out.append('R' * (n - d))
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


def sort_word(v):
    v = list(v)
    n = len(v)
    m = max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    target_budget = m * (m + 1) // 2 + (r - 1) * (m - 2)

    modes = (
        'greedy_tie_dist', 'greedy_tie_dist_rev',
        'greedy', 'greedy_rev',
        'greedy_cost2', 'greedy_cost', 'greedy_cost4', 'greedy_cost5',
        'greedy_cost_rev', 'greedy_cost15',
        'greedy_max',
        'L', 'R', 'LR', 'RL'
    )
    shifts = range(max(1, r))
    best = None
    best_len = 10**9

    labeled_target = list(range(1, m + 1)) + [0] * r
    for strat in ('min', 'max_diff', 'score'):
        w_b = _reduce(_bubble_sort(v, labeled_target, strat))
        if _replay(v, w_b) == goal and len(w_b) < best_len:
            best = w_b
            best_len = len(w_b)

    for center_bias in (0, 1, -1):
        for k in range(n):
            for shift in shifts:
                rem = _get_lifts(v, k, shift, m, r, center_bias=center_bias)
                for mode in modes:
                    w = _run_sweep(v, rem, k, mode, limit=best_len)
                    if w is not None:
                        w = _reduce(w)
                        lw = len(w)
                        if lw < best_len:
                            if _replay(v, w) == goal:
                                best = w
                                best_len = lw

    if best is not None:
        return best
    return _reduce(_naive(v))
