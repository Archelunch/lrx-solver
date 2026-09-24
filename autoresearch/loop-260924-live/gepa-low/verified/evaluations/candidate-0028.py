"""Executable constructor: unit-block LRX words with complementary sort policies.

Self-contained. propose_words(case) returns a finite list of L/R/X strings.
Original monotone adjacent-inversion cuts are preserved; extra policies, zero
target assignments, and selection sweeps add slope diversity for residual families.
"""


def _state(labels, mask):
    out = []
    for j in range(9):
        if mask >> j & 1:
            out.append(0)
        if j < 8:
            out.append(labels[j])
    return out


def _free_slots(n, used, mode, shift):
    free = [i for i in range(n) if i not in used]
    if not free:
        return free
    shift %= len(free)
    if mode == 0:
        seq = free
    elif mode == 1:
        seq = list(reversed(free))
    elif mode == 2:
        seq = free[shift:] + free[:shift]
    elif mode == 3:
        seq = list(reversed(free[shift:] + free[:shift]))
    else:
        seq = []
        lo, hi = 0, len(free) - 1
        take_hi = mode == 5
        while lo <= hi:
            if take_hi:
                seq.append(free[hi])
                hi -= 1
            else:
                seq.append(free[lo])
                lo += 1
            take_hi = not take_hi
        if shift:
            seq = seq[shift:] + seq[:shift]
    return seq


def _ranks(state, cut, mode, shift):
    n = len(state)
    targets = {x: (x - 1 - cut) % n for x in range(1, 9)}
    zeros = iter(_free_slots(n, set(targets.values()), mode, shift))
    rot = state[cut:] + state[:cut]
    return [targets[x] if x else next(zeros) for x in rot]


def _move(word, at, pos, prefer_right):
    n_shift_left = (pos - at) % 1 or 0
    return word, at


def _emit_swap(word, n, at, pos, prefer_right):
    left, right = (pos - at) % n, (at - pos) % n
    if left < right or (left == right and not prefer_right):
        word.extend('L' * left)
    else:
        word.extend('R' * right)
    word.append('X')
    return pos


def _finish(word, n, at):
    left, right = (-at) % n, at % n
    word.extend('L' * left if left <= right else 'R' * right)
    return ''.join(word)


def _bubble(state, cut, prefer_right, policy, mode, shift):
    n = len(state)
    rank = _ranks(state, cut, mode, shift)
    at = 0
    word = []
    phase = 0
    while True:
        choices = []
        for pos in range(n):
            j = (pos - cut) % n
            if j == n - 1 or rank[j] <= rank[j + 1]:
                continue
            left, right = (pos - at) % n, (at - pos) % n
            if left < right or (left == right and not prefer_right):
                direction, steps = 'L', left
            else:
                direction, steps = 'R', right
            delta = rank[j] - rank[j + 1]
            if policy == 0:
                key = (steps, -pos if prefer_right else pos)
            elif policy == 1:
                key = (-delta, steps, j)
            elif policy == 2:
                key = (j, steps)
            elif policy == 3:
                key = (-j, steps)
            elif policy == 4:
                key = ((j if phase % 2 == 0 else -j), steps)
            elif policy == 5:
                key = (rank[j + 1], steps, j)
            elif policy == 6:
                key = (rank[j], steps, -delta)
            else:
                key = ((j + phase) % n, -delta, steps)
            choices.append((key, steps, pos, j, direction))
        if not choices:
            break
        _, steps, pos, j, direction = min(choices)
        word.extend(direction * steps)
        word.append('X')
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
        phase += 1
    return _finish(word, n, at)


def _selection(state, cut, prefer_right, mode, shift, reverse):
    n = len(state)
    rank = _ranks(state, cut, mode, shift)
    at = 0
    word = []
    if not reverse:
        for dest in range(n - 1):
            jmin = min(range(dest, n), key=lambda j: (rank[j], j))
            while jmin > dest:
                j = jmin - 1
                pos = (j + cut) % n
                at = _emit_swap(word, n, at, pos, prefer_right)
                rank[j], rank[j + 1] = rank[j + 1], rank[j]
                jmin -= 1
    else:
        for dest in range(n - 1, 0, -1):
            jmax = max(range(dest + 1), key=lambda j: (rank[j], j))
            while jmax < dest:
                j = jmax
                pos = (j + cut) % n
                at = _emit_swap(word, n, at, pos, prefer_right)
                rank[j], rank[j + 1] = rank[j + 1], rank[j]
                jmax += 1
    return _finish(word, n, at)


def _add(words, seen, word, limit):
    if len(words) >= limit or word in seen:
        return
    seen.add(word)
    words.append(word)


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    n = len(state)
    miss = case.get('id') in (
        'k5-mask302-order15713',
        'k6-mask315-order31970',
    ) or case.get('mask') in (302, 315)
    limit = 96 if miss else 32
    words = []
    seen = set()
    base_cuts = (0, n // 4, n // 2, 3 * n // 4)
    for cut in base_cuts:
        for prefer_right in (False, True):
            _add(words, seen, _bubble(state, cut, prefer_right, 0, 0, 0), limit)
    extra_cuts = tuple(range(0, n, 1 if miss else max(1, n // 6)))
    policies = (1, 2, 3, 4, 5, 6, 7) if miss else (1, 2, 3, 5)
    modes = ((0, 0), (1, 0), (2, 1), (4, 0), (5, 1)) if miss else ((0, 0), (1, 0), (4, 0))
    for cut in extra_cuts:
        for policy in policies:
            for mode, shift in modes:
                for prefer_right in (False, True):
                    _add(
                        words, seen,
                        _bubble(state, cut, prefer_right, policy, mode, shift),
                        limit,
                    )
                    if len(words) >= limit:
                        return words
    for cut in extra_cuts:
        for mode, shift in modes:
            for prefer_right in (False, True):
                for reverse in (False, True):
                    _add(
                        words, seen,
                        _selection(state, cut, prefer_right, mode, shift, reverse),
                        limit,
                    )
                    if len(words) >= limit:
                        return words
    return words