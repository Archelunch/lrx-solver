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


def _ranks(state, cut):
    n = len(state)
    targets = {x: (x-1-cut) % n for x in range(1, 9)}
    zeros = iter(sorted(set(range(n)) - set(targets.values())))
    return [targets[x] if x else next(zeros) for x in state[cut:] + state[:cut]]


def _construct(state, cut, prefer_right):
    n = len(state)
    rank = _ranks(state, cut)
    at = 0
    word = []
    while True:
        choices = []
        for pos in range(n):
            j = (pos-cut) % n
            if j == n-1 or rank[j] <= rank[j+1]:
                continue
            left, right = (pos-at) % n, (at-pos) % n
            if left < right or (left == right and not prefer_right):
                direction, steps = 'L', left
            else:
                direction, steps = 'R', right
            choices.append((steps, -pos if prefer_right else pos, pos, j, direction))
        if not choices:
            break
        steps, _, pos, j, direction = min(choices)
        word.extend(direction * steps)
        word.append('X')
        rank[j], rank[j+1] = rank[j+1], rank[j]
        at = pos
    left, right = (-at) % n, at
    word.extend('L' * left if left <= right else 'R' * right)
    return ''.join(word)


def _zero_positions(state):
    """Physical indices of unit zero blocks, in slope order."""
    return [i for i, x in enumerate(state) if x == 0]


def _zone_weights(state, free):
    """Free zero blocks cost 0, other zeros cost 80, tokens cost 1."""
    weights = []
    block = 0
    free = set(free)
    for x in state:
        if x == 0:
            weights.append(0 if block in free else 80)
            block += 1
        else:
            weights.append(1)
    return weights


def _hop(at, pos, n, weights):
    """Rotate toward pos, preferring the arc with smaller zero-block weight."""
    left = (pos - at) % n
    right = (at - pos) % n

    def cost(steps, sign):
        return sum(weights[(at + sign * s) % n] for s in range(1, steps + 1))

    left_cost, right_cost = cost(left, 1), cost(right, -1)
    if left_cost < right_cost or (left_cost == right_cost and left <= right):
        return 'L', left
    return 'R', right


def _routed(state, cut, weights, policy):
    """Same rank sort as the seed, but hop directions avoid weighted blocks.

    policy 'near' keeps nearest-inversion order; 'cheap' picks the
    lowest-weight hop; 'steep' clears the largest rank drop first;
    'small' bubbles the smallest rank first.
    """
    n = len(state)
    rank = _ranks(state, cut)
    at = 0
    chunks = []
    while True:
        best = None
        for pos in range(n):
            j = (pos - cut) % n
            if j == n - 1 or rank[j] <= rank[j + 1]:
                continue
            steps = min((pos - at) % n, (at - pos) % n)
            direction, wsteps = _hop(at, pos, n, weights)
            sign = 1 if direction == 'L' else -1
            wcost = sum(weights[(at + sign * s) % n] for s in range(1, wsteps + 1))
            if policy == 'steep':
                key = (-(rank[j] - rank[j + 1]), wcost, steps, pos)
            elif policy == 'small':
                key = (rank[j], wcost, steps, pos)
            elif policy == 'near':
                key = (steps, pos, wcost)
            else:
                key = (wcost, steps, pos)
            if best is None or key < best[0]:
                best = (key, pos, j)
        if best is None:
            break
        _, pos, j = best
        direction, steps = _hop(at, pos, n, weights)
        if steps:
            chunks.append(direction * steps)
        chunks.append('X')
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
    direction, steps = _hop(at, 0, n, weights)
    if steps:
        chunks.append(direction * steps)
    return ''.join(chunks)


def propose_words(case):
    """Seed cuts plus routes that park head travel on one free zero block."""
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    n = len(state)
    cuts = (0, n // 4, n // 2, 3 * n // 4)
    words = []

    def add(word):
        if word and word not in words and len(word) <= 4096 and len(words) < 32:
            words.append(word)

    for cut in cuts:
        for prefer_right in (False, True):
            add(_construct(state, cut, prefer_right))
    zeros = _zero_positions(state)
    k = len(zeros)
    for i in range(k):
        add(_routed(state, 0, _zone_weights(state, (i,)), 'near'))
    for i in range(k):
        add(_routed(state, 0, _zone_weights(state, (i,)), 'cheap'))
    for i in range(k):
        add(_routed(state, zeros[i], _zone_weights(state, (i,)), 'cheap'))
    for i in range(k):
        add(_routed(state, 0, _zone_weights(state, (i, (i + 1) % k)), 'cheap'))
    for i in range(k):
        add(_routed(state, 0, _zone_weights(state, (i,)), 'steep'))
    for i in range(k):
        add(_routed(state, n // 2, _zone_weights(state, (i,)), 'small'))
    return words
