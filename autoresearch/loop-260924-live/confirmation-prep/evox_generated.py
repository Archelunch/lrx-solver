"""Executable seed: several complete unit-block LRX words per family.

This file is deliberately self-contained so it can run in a restricted child
without importing the verifier or any repository module.  It is a constructor,
not a claim that its words yield a successful rational mixture.
"""


def _state(labels, mask):
    out = []
    for j in range(9):
        if mask >> j & 1:
            out.append(0)
        if j < 8:
            out.append(labels[j])
    return out


def _ranks(state, cut, zero_order):
    """Label targets are fixed on the circle; zeros fill the remaining slots.

    zero_order permutes those slots in scan order. Zeros are identical, so
    every assignment is a legal identity, but each one moves different blocks.
    """
    n = len(state)
    targets = {x: (x - 1 - cut) % n for x in range(1, 9)}
    holes = sorted(set(range(n)) - set(targets.values()))
    assigned = [holes[i] for i in zero_order]
    zeros = iter(assigned)
    return [targets[x] if x else next(zeros) for x in state[cut:] + state[:cut]]


def _construct(state, cut, prefer_right, zero_order, policy):
    """Adjacent-inversion sort recorded as rotations plus one head swap.

    policy selects which inversion to clear: shortest rotation, leftmost,
    or rightmost. prefer_right only breaks equal-length rotation ties.
    """
    n = len(state)
    rank = _ranks(state, cut, zero_order)
    at = 0
    word = []
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
            if policy == 'left':
                key = (j, steps)
            elif policy == 'right':
                key = (-j, steps)
            else:
                key = (steps, -pos if prefer_right else pos)
            choices.append((key, steps, pos, j, direction))
        if not choices:
            break
        _, steps, pos, j, direction = min(choices)
        word.extend(direction * steps)
        word.append('X')
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
    left, right = (-at) % n, at
    word.extend('L' * left if left <= right else 'R' * right)
    return ''.join(word)


def _zero_orders(k):
    """A few slot permutations: identity, reversal, and adjacent rotations."""
    ident = tuple(range(k))
    orders = [ident, ident[::-1]]
    for shift in range(1, k):
        orders.append(ident[shift:] + ident[:shift])
    # one transposition of the extreme holes, useful when end slopes are tight
    if k >= 2:
        swapped = list(ident)
        swapped[0], swapped[-1] = swapped[-1], swapped[0]
        orders.append(tuple(swapped))
    unique = []
    for order in orders:
        if order not in unique:
            unique.append(order)
    return unique


def propose_words(case):
    """Seed cuts plus zero-slot and inversion-policy variants, capped at 32."""
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    n = len(state)
    k = n - 8
    cuts = (0, n // 4, n // 2, 3 * n // 4)
    words = []

    def add(cut, prefer_right, zero_order, policy):
        if len(words) >= 32:
            return
        word = _construct(state, cut, prefer_right, zero_order, policy)
        if word not in words and len(word) <= 4096:
            words.append(word)

    ident = tuple(range(k))
    for cut in cuts:
        for prefer_right in (False, True):
            add(cut, prefer_right, ident, 'near')
    # Complementary columns: other legal zero targets and scan directions.
    for zero_order in _zero_orders(k):
        if zero_order == ident:
            continue
        for cut in (0, n // 2):
            for policy in ('near', 'left', 'right'):
                add(cut, False, zero_order, policy)
                if len(words) >= 32:
                    return words
    for cut in cuts:
        for policy in ('left', 'right'):
            add(cut, False, ident, policy)
            if len(words) >= 32:
                return words
    return words
