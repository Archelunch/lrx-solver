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


def _reduce(word, n=None):
    while True:
        orig_len = len(word)
        # Pass 1: cancel adjacent inverses LR, RL, XX
        out = []
        for ch in word:
            if out and out[-1] + ch in ('LR', 'RL', 'XX'):
                out.pop()
            else:
                out.append(ch)
        word = ''.join(out)
        if not n:
            if len(word) == orig_len:
                break
            continue

        # Pass 2: simplify runs of L/R modulo n
        parts = []
        curr_shifts = 0
        for ch in word:
            if ch == 'L':
                curr_shifts += 1
            elif ch == 'R':
                curr_shifts -= 1
            else:
                if curr_shifts:
                    d = curr_shifts % n
                    parts.append('L' * d if d <= n - d else 'R' * (n - d))
                    curr_shifts = 0
                parts.append('X')
        if curr_shifts:
            d = curr_shifts % n
            parts.append('L' * d if d <= n - d else 'R' * (n - d))
        word = ''.join(parts)

        # Pass 3: cancel any newly formed adjacent inverses
        out = []
        for ch in word:
            if out and out[-1] + ch in ('LR', 'RL', 'XX'):
                out.pop()
            else:
                out.append(ch)
        word = ''.join(out)
        if len(word) == orig_len:
            break
    return word


def _lifts(v, k, shift, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (k + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (k + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, k, mode, limit=2000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] == 0 and a[y] == 0:
            rem[x], rem[y] = ry + 1, rx - 1
            return
        out.append('X')
        a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    bounce_dir = 1 if 'L' in mode else -1
    bounce_steps = 0
    bounce_limit = (n + 1) // 2 if 'half' in mode else (n - 1 if 'cocktail' in mode else n)

    while any(rem) and len(out) < limit:
        if mode.startswith('greedy'):
            best_key, best_pos, best_move = None, None, None
            for p in range(n):
                if must_cross(p):
                    d_fwd = (p - c) % n
                    d_bwd = (c - p) % n
                    if 'R' in mode:
                        d, move = (d_bwd, 'R' * d_bwd) if d_bwd <= d_fwd else (d_fwd, 'L' * d_fwd)
                    else:
                        d, move = (d_fwd, 'L' * d_fwd) if d_fwd <= d_bwd else (d_bwd, 'R' * d_bwd)
                    urgency = rem[p] - rem[(p + 1) % n] if 'max' in mode else 0
                    key = (d, -urgency)
                    if best_key is None or key < best_key:
                        best_key, best_pos, best_move = key, p, move
            if best_key is None:
                return None
            out.append(best_move)
            c = best_pos
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
        elif mode.startswith('bounce') or mode.startswith('cocktail'):
            bounce_steps += 1
            if bounce_steps >= bounce_limit:
                bounce_dir = -bounce_dir
                bounce_steps = 0
            if bounce_dir == 1:
                out.append('L')
                c = (c + 1) % n
            else:
                out.append('R')
                c = (c - 1) % n
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


def sort_word(v):
    v = list(v)
    n, m = len(v), max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    best = None
    for k in range(n):
        for shift in range(max(1, r)):
            rem = _lifts(v, k, shift, m, r) if r else None
            if rem is None:
                continue
            for mode in ('greedy', 'greedy_R', 'greedy_max', 'L', 'R', 'bounce_L', 'bounce_R', 'bounce_L_half', 'bounce_R_half', 'cocktail_L', 'cocktail_R'):
                w = _sweep(v, rem, k, mode)
                if w is not None:
                    w = _reduce(w, n)
                    if (best is None or len(w) < len(best)) and _replay(v, w) == goal:
                        best = w
    return best if best is not None else _naive(v)
