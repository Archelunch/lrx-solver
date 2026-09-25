"""LRX constructive universal cover sorter with multi-mode sweep and targeted reversal resolution."""

import time


def _reduce(word):
    out = []
    for ch in word:
        if out:
            top = out[-1]
            if (
                (top == "L" and ch == "R")
                or (top == "R" and ch == "L")
                or (top == "X" and ch == "X")
            ):
                out.pop()
                continue
        out.append(ch)
    return "".join(out)


def _canonical_word(word, n=None):
    prev_len = len(word) + 1
    while len(word) < prev_len:
        prev_len = len(word)
        word = _reduce(word)
        if n is not None and n > 0:
            word = word.replace("L" * n, "").replace("R" * n, "")
            half = n // 2
            if n % 2 == 0:
                word = word.replace("L" * (half + 1), "R" * (half - 1))
                word = word.replace("R" * (half + 1), "L" * (half - 1))
            else:
                word = word.replace("L" * (half + 1), "R" * half)
                word = word.replace("R" * (half + 1), "L" * half)
    return word


def _replay(v, word):
    a = list(v)
    for ch in word:
        if ch == "L":
            a.append(a.pop(0))
        elif ch == "R":
            a.insert(0, a.pop())
        else:
            a[0], a[1] = a[1], a[0]
    return a


def _get_lifts(v, k, shift, m, r):
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
    order = sorted(range(n), key=lambda p: rem[p], reverse=(q > 0))
    for p in order[: abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, k, mode, limit=1000):
    n = len(v)
    a = list(v)
    rem = list(rem)
    out = []
    c = 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] == 0 and a[y] == 0:
            rem[x], rem[y] = ry + 1, rx - 1
            return
        out.append("X")
        a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    steps = 0
    while any(rem) and steps < limit:
        steps += 1
        if mode == "greedy_L":
            found = False
            for dist in range(n):
                pos = (c + dist) % n
                if must_cross(pos):
                    out.append("L" * dist)
                    c = pos
                    found = True
                    break
                pos = (c - dist) % n
                if must_cross(pos):
                    out.append("R" * dist)
                    c = pos
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == "greedy_R":
            found = False
            for dist in range(n):
                pos = (c - dist) % n
                if must_cross(pos):
                    out.append("R" * dist)
                    c = pos
                    found = True
                    break
                pos = (c + dist) % n
                if must_cross(pos):
                    out.append("L" * dist)
                    c = pos
                    found = True
                    break
            if not found:
                return None
            cross(c)
        elif mode == "greedy_cost_L":
            best_val = -10**9
            best_pos, best_dist, best_dir = None, 0, "L"
            for dist in range(n):
                for dir_ch, pos in (("L", (c + dist) % n), ("R", (c - dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        val = diff * 2 - dist
                        if val > best_val:
                            best_val = val
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "greedy_cost_R":
            best_val = -10**9
            best_pos, best_dist, best_dir = None, 0, "R"
            for dist in range(n):
                for dir_ch, pos in (("R", (c - dist) % n), ("L", (c + dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        val = diff * 2 - dist
                        if val > best_val:
                            best_val = val
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "greedy_cost_ratio":
            best_val = -10**9
            best_pos, best_dist, best_dir = None, 0, "L"
            for dist in range(n):
                for dir_ch, pos in (("L", (c + dist) % n), ("R", (c - dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        val = (diff - 1) / (dist + 1.0)
                        if val > best_val:
                            best_val = val
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "greedy_cost_ratio_R":
            best_val = -10**9
            best_pos, best_dist, best_dir = None, 0, "R"
            for dist in range(n):
                for dir_ch, pos in (("R", (c - dist) % n), ("L", (c + dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        val = (diff - 1) / (dist + 1.0)
                        if val > best_val:
                            best_val = val
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "lookahead_L":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "L"
            for dist in range(n):
                for dir_ch, pos in (("L", (c + dist) % n), ("R", (c - dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        bonus = 0
                        p_prev = (pos - 1) % n
                        p_next2 = (pos + 2) % n
                        if rem[p_prev] - (rem[(pos + 1) % n] - 1) >= 2:
                            bonus += 1
                        if (rem[pos] + 1) - rem[p_next2] >= 2:
                            bonus += 1
                        score = diff * 3 + bonus * 2 - dist * 2
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "lookahead_R":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "R"
            for dist in range(n):
                for dir_ch, pos in (("R", (c - dist) % n), ("L", (c + dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        bonus = 0
                        p_prev = (pos - 1) % n
                        p_next2 = (pos + 2) % n
                        if rem[p_prev] - (rem[(pos + 1) % n] - 1) >= 2:
                            bonus += 1
                        if (rem[pos] + 1) - rem[p_next2] >= 2:
                            bonus += 1
                        score = diff * 3 + bonus * 2 - dist * 2
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "lookahead_ratio_L":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "L"
            for dist in range(n):
                for dir_ch, pos in (("L", (c + dist) % n), ("R", (c - dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        bonus = 0
                        p_prev = (pos - 1) % n
                        p_next2 = (pos + 2) % n
                        if rem[p_prev] - (rem[(pos + 1) % n] - 1) >= 2:
                            bonus += 1
                        if (rem[pos] + 1) - rem[p_next2] >= 2:
                            bonus += 1
                        score = (diff + bonus) / (dist + 1.0)
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "lookahead_ratio_R":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "R"
            for dist in range(n):
                for dir_ch, pos in (("R", (c - dist) % n), ("L", (c + dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        bonus = 0
                        p_prev = (pos - 1) % n
                        p_next2 = (pos + 2) % n
                        if rem[p_prev] - (rem[(pos + 1) % n] - 1) >= 2:
                            bonus += 1
                        if (rem[pos] + 1) - rem[p_next2] >= 2:
                            bonus += 1
                        score = (diff + bonus) / (dist + 1.0)
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "target_dist_L":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "L"
            for dist in range(n):
                for dir_ch, pos in (("L", (c + dist) % n), ("R", (c - dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        d_target = min((k - pos) % n, (pos - k) % n)
                        score = diff * 4 - dist * 3 - d_target
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "target_dist_R":
            best_score = -10**9
            best_pos, best_dist, best_dir = None, 0, "R"
            for dist in range(n):
                for dir_ch, pos in (("R", (c - dist) % n), ("L", (c + dist) % n)):
                    diff = rem[pos] - rem[(pos + 1) % n]
                    if diff >= 2:
                        d_target = min((k - pos) % n, (pos - k) % n)
                        score = diff * 4 - dist * 3 - d_target
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_dist = dist
                            best_dir = dir_ch
            if best_pos is None:
                return None
            out.append(best_dir * best_dist)
            c = best_pos
            cross(c)
        elif mode == "continuous_L":
            if must_cross(c):
                cross(c)
            else:
                out.append("L")
                c = (c + 1) % n
        elif mode == "continuous_R":
            if must_cross(c):
                cross(c)
            else:
                out.append("R")
                c = (c - 1) % n

    if any(rem):
        return None
    d = (k - c) % n
    out.append("L" * d if d <= n - d else "R" * (n - d))
    return "".join(out)


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
                out.append(("L" * k if k <= n - k else "R" * (n - k)) + "X")
                c = i
                key[i], key[i + 1] = key[i + 1], key[i]
                last = i
        end = last
    k = (-c) % n
    out.append("L" * k if k <= n - k else "R" * (n - k))
    return "".join(out)


def sort_word(v):
    start_time = time.perf_counter()
    v = list(v)
    n = len(v)
    m = max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    budget = m * (m + 1) // 2 + (r - 1) * (m - 2)

    best = None
    best_len = 10**9

    modes = (
        "continuous_L",
        "continuous_R",
        "lookahead_ratio_L",
        "lookahead_ratio_R",
        "greedy_cost_ratio",
        "greedy_cost_ratio_R",
        "lookahead_L",
        "lookahead_R",
        "target_dist_L",
        "target_dist_R",
        "greedy_cost_L",
        "greedy_cost_R",
        "greedy_L",
        "greedy_R",
    )
    shifts = range(max(1, r))

    candidates = []
    for k in range(n):
        for shift in shifts:
            rem = _get_lifts(v, k, shift, m, r)
            inv = sum(abs(x) for x in rem) // 2
            d = min(k, n - k)
            candidates.append((inv + d, inv, k, shift, rem))

    candidates.sort(key=lambda t: t[0])

    for est, inversions, k, shift, rem in candidates:
        if inversions >= best_len:
            continue
        for mode in modes:
            if time.perf_counter() - start_time > 0.125:
                break
            w = _sweep(v, rem, k, mode, limit=min(1000, best_len + 15))
            if w is not None:
                w = _canonical_word(w, n)
                lw = len(w)
                if lw < best_len:
                    if _replay(v, w) == goal:
                        best = w
                        best_len = lw
                        if best_len <= budget and est > best_len:
                            break
        if best_len <= budget and est > best_len + 6:
            break
        if time.perf_counter() - start_time > 0.125:
            break

    if best_len > budget:
        prefixes = [
            "RXLXLXLLX", "XLXLXLXLL", "XRXR", "XLXL", "RXRX", "LXLX",
            "XRX", "XLX", "RXR", "LXL", "RXLX", "LXRX",
            "XRXRX", "XLXLX", "RXRXRX", "XLXLXL",
            "RXRXLL", "XLXLXLL", "XRXRXL", "XLXLXR", "LXLL", "RXRR",
            "X", "LX", "RX", "XR", "XL", "L", "R", "LL", "RR",
            "RXRXL", "RXRXR", "XLXLL", "LXRXL", "RXRXLX",
            "XRXRXLXL", "RXRXRXLL", "XLXLXLXLL",
            "RXRXRXRX", "XLXLXLXL", "RXRXRXLLX", "XLXLXLXRX",
            "RXLXLXLL", "LXRXRXRR"
        ]
        nonzeros = [x for x in v if x]
        inv_count = sum(
            1
            for i in range(len(nonzeros))
            for j in range(i + 1, len(nonzeros))
            if nonzeros[i] > nonzeros[j]
        )
        if inv_count >= len(nonzeros) * (len(nonzeros) - 1) // 3:
            prefixes = [
                "RXLXLXLLX", "XLXLXLXLL", "RXRXRXRX", "XLXLXLXL",
                "XRXR", "XLXL", "RXRX", "LXLX", "XRXRX", "XLXLX",
                "XRX", "XLX", "RXR", "LXL", "RXLX", "LXRX",
                "RXRXRX", "XLXLXL", "RXRXLL", "XLXLXLL", "LXLL", "RXRR",
                "RXRXRXLLX", "XLXLXLXRX", "RXLXLXLL", "LXRXRXRR",
                "XRXRXLXL", "RXRXRXLL", "XLXLXLXLL",
                "X", "LX", "RX", "XR", "XL"
            ] + prefixes

        seen_prefixes = set()
        unique_prefixes = []
        for p in prefixes:
            if p not in seen_prefixes:
                seen_prefixes.add(p)
                unique_prefixes.append(p)

        for pfx in unique_prefixes:
            if time.perf_counter() - start_time > 0.188:
                break
            vp = _replay(v, pfx)
            cand_p = []
            for k in range(n):
                for shift in shifts:
                    rem = _get_lifts(vp, k, shift, m, r)
                    inv = sum(abs(x) for x in rem) // 2
                    d = min(k, n - k)
                    cand_p.append((inv + d, inv, k, shift, rem))
            cand_p.sort(key=lambda t: t[0])
            for est, inversions, k, shift, rem in cand_p[:12]:
                if len(pfx) + inversions >= best_len:
                    continue
                for mode in (
                    "continuous_L",
                    "continuous_R",
                    "lookahead_ratio_L",
                    "lookahead_ratio_R",
                    "greedy_cost_ratio",
                    "greedy_cost_ratio_R",
                    "lookahead_L",
                    "lookahead_R",
                    "target_dist_L",
                    "target_dist_R",
                    "greedy_cost_L",
                    "greedy_cost_R",
                ):
                    if time.perf_counter() - start_time > 0.188:
                        break
                    w = _sweep(
                        vp,
                        rem,
                        k,
                        mode,
                        limit=min(1000, best_len - len(pfx) + 12),
                    )
                    if w is not None:
                        w = _canonical_word(pfx + w, n)
                        lw = len(w)
                        if lw < best_len:
                            if _replay(v, w) == goal:
                                best = w
                                best_len = lw
                                if best_len <= budget:
                                    break
                if best_len <= budget:
                    break
            if best_len <= budget:
                break

    if best is not None:
        return best
    return _canonical_word(_naive(v), n)

def _drop_zero_swaps(v, word):
    a, n, c, out = list(v), len(v), 0, []
    for ch in word:
        if ch == 'X':
            j = (c + 1) % n
            if a[c] == 0 and a[j] == 0:
                continue
            a[c], a[j] = a[j], a[c]
        else:
            c = (c + (1 if ch == 'L' else -1)) % n
        out.append(ch)
    red = []
    for ch in out:
        if red and red[-1] + ch in ('LR', 'RL', 'XX'):
            red.pop()
        else:
            red.append(ch)
    return ''.join(red)


def certify(family):
    v = list(family['unit_base'])
    return {'words': [_drop_zero_swaps(v, sort_word(list(v)))]}
