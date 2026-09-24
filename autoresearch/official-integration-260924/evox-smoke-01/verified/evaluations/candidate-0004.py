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


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    cuts = (0, len(state)//4, len(state)//2, 3*len(state)//4)
    words = []
    for cut in cuts:
        for prefer_right in (False, True):
            word = _construct(state, cut, prefer_right)
            if word not in words:
                words.append(word)
    return words  # MOCK_SOLUTION_REWRITE
