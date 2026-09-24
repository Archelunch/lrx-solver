"""Sol-completed interpretation of a *partial*, unverified proposer idea.

The interrupted external stream suggested biasing selection-sort rotations
away from expensive zero blocks, but supplied neither a complete algorithm
nor its claimed word.  These two k5 words are our explicit hypothesis.
Frozen incumbent words are supplied separately by the trusted evaluator.
"""


def _state(labels, mask):
    out = []
    for j in range(9):
        if mask >> j & 1:
            out.append(0)
        if j < 8:
            out.append(labels[j])
    return out


def _construct(state, cut, prefer_right):
    n = len(state)
    targets = {value: (value - 1 - cut) % n for value in range(1, 9)}
    zeros = iter(sorted(set(range(n)) - set(targets.values())))
    ordered = state[cut:] + state[:cut]
    ranks = [targets[value] if value else next(zeros) for value in ordered]
    block = iter(range(len(state) - 8))
    original_identities = [next(block) if value == 0 else -1 for value in state]
    identities = original_identities[cut:] + original_identities[:cut]
    # Dual multipliers scaled by 392, in the retained-block order.
    penalty = (0, 308, 394, 49, 261)
    at = 0
    letters = []

    def hop(pos):
        choices = []
        for direction, sign in (('L', 1), ('R', -1)):
            steps = ((pos - at) % n) if direction == 'L' else ((at - pos) % n)
            carried = 0
            for step in range(steps):
                physical = ((at + step) % n) if direction == 'L' else ((at - step - 1) % n)
                zero = identities[(physical - cut) % n]
                if zero >= 0:
                    carried += penalty[zero]
            tie = 0 if (direction == 'R') == prefer_right else 1
            choices.append((392 * steps + carried, steps, tie, direction))
        cost, steps, _, direction = min(choices)
        return cost, steps, direction

    while True:
        choices = []
        for pos in range(n):
            j = (pos - cut) % n
            if j == n - 1 or ranks[j] <= ranks[j + 1]:
                continue
            route_cost, steps, direction = hop(pos)
            choices.append((route_cost, steps, -pos if prefer_right else pos,
                            j, direction))
        if not choices:
            break
        _, steps, _, j, direction = min(choices)
        pos = (j + cut) % n
        letters.extend(direction * steps)
        letters.append('X')
        ranks[j], ranks[j + 1] = ranks[j + 1], ranks[j]
        identities[j], identities[j + 1] = identities[j + 1], identities[j]
        at = pos
    _, steps, direction = hop(0)
    letters.extend(direction * steps)
    return ''.join(letters)


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    if case['mask'] != 302 or case['labels'] != [4, 1, 7, 8, 5, 6, 3, 2]:
        return []
    state = _state(case['labels'], case['mask'])
    words = []
    for cut in range(len(state)):
        for prefer_right in (False, True):
            word = _construct(state, cut, prefer_right)
            if word not in words:
                words.append(word)
    return words
