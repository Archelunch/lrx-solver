"""sched_word with a cut per core (the target order inside core i is t_i+1..m, 0, 1..t_i)."""


def sched_word2(state, cores, fin, pre=''):
    n = len(state)
    m = sum(1 for x in state if x)
    cell, w, c = list(state), [], 0
    for ch in pre:
        if ch == 'L':
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
        else:
            j = (c + 1) % n
            cell[c], cell[j] = cell[j], cell[c]
        w.append(ch)

    def goto(p):
        nonlocal c
        f, b = (p - c) % n, (c - p) % n
        w.append('L' * f if f <= b else 'R' * b)
        c = p

    for seed, sides, t in cores:
        order = list(range(t + 1, m + 1)) + [0] + list(range(1, t + 1))
        rk = {x: i for i, x in enumerate(order)}
        lo = hi = seed
        ln = 1
        for side in sides:
            if side == 'r':
                j = (hi + 1) % n
                s = 0
                while s < ln and rk[cell[(hi - s) % n]] > rk[cell[j]]:
                    s += 1
                if s:
                    goto(hi)
                    w.append('X' + 'RX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j - i) % n] = cell[(j - i - 1) % n]
                    cell[(j - s) % n] = v
                    c = (j - s) % n
                hi = j
            else:
                j = (lo - 1) % n
                s = 0
                while s < ln and rk[cell[(lo + s) % n]] < rk[cell[j]]:
                    s += 1
                if s:
                    goto(j)
                    w.append('X' + 'LX' * (s - 1))
                    v = cell[j]
                    for i in range(s):
                        cell[(j + i) % n] = cell[(j + i + 1) % n]
                    cell[(j + s) % n] = v
                    c = (j + s - 1) % n
                lo = j
            ln += 1
    i = cell.index(1)
    if [cell[(i + x) % n] for x in range(m)] != list(range(1, m + 1)):
        return None
    if any(cell[(i + m + x) % n] for x in range(n - m)):
        return None
    w.append('L' * ((i - c) % n) if fin == 'L' else 'R' * ((c - i) % n))
    return ''.join(w)
