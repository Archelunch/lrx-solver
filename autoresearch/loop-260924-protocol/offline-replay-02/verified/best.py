"""LRX constructor: incumbent all-cuts seed plus local selection perturbations.

Words are unit-skeleton sorts. Perturbations change only which adjacent
inversion is brought to the front, so each word is a complete direct candidate.
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
    targets = {x: (x - 1 - cut) % n for x in range(1, 9)}
    zeros = iter(sorted(set(range(n)) - set(targets.values())))
    return [targets[x] if x else next(zeros) for x in state[cut:] + state[:cut]]


def _tags(state):
    tags = []
    z = 0
    for x in state:
        if x == 0:
            tags.append(z)
            z += 1
        else:
            tags.append(-1)
    return tags, z


def _construct(state, cut, prefer_right, scale=0.0, weights=None, perturb=None):
    n = len(state)
    rank = _ranks(state, cut)
    tags, nz = _tags(state)
    if not weights:
        weights = (0.0, 11 / 14, 197 / 196, 1 / 8, 261 / 392, 0.5, 0.5, 0.5)
    weights = list(weights[:nz]) + [0.0] * max(0, nz - len(weights))
    at = 0
    word = []
    step_no = 0
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
            if direction == 'L':
                arc = tags[:steps]
            else:
                arc = tags[n - steps:] if steps else []
            pen = 0.0
            for t in arc:
                if t >= 0:
                    pen += weights[t]
            tie = -pos if prefer_right else pos
            choices.append((steps + scale * pen, steps, tie, pos, j, direction, steps))
        if not choices:
            break
        choices.sort()
        pick = 0
        if perturb is not None and step_no == perturb[0] and len(choices) > 1:
            pick = 1 if perturb[1] >= 1 else 0
        _, _, _, pos, j, direction, steps = choices[pick]
        word.extend(direction * steps)
        word.append('X')
        if direction == 'L' and steps:
            tags = tags[steps:] + tags[:steps]
        elif direction == 'R' and steps:
            tags = tags[n - steps:] + tags[:n - steps]
        tags[0], tags[1] = tags[1], tags[0]
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
        step_no += 1
    left, right = (-at) % n, at
    word.extend('L' * left if left <= right else 'R' * right)
    return ''.join(word)


def _proxy(state, word):
    tags, nz = _tags(state)
    ring = list(tags)
    g_exit = [0] * nz
    g_near = [0] * nz
    n = len(state)
    if n == 0 or nz == 0:
        return len(word)
    for ch in word:
        if ch == 'X':
            ring[0], ring[1] = ring[1], ring[0]
            continue
        if ch == 'L':
            if ring[0] >= 0:
                g_exit[ring[0]] += 1
            for t in ring:
                if t >= 0:
                    g_near[t] += 1
                    break
            ring = ring[1:] + ring[:1]
        else:
            if ring[-1] >= 0:
                g_exit[ring[-1]] += 1
            for t in reversed(ring):
                if t >= 0:
                    g_near[t] += 1
                    break
            ring = ring[-1:] + ring[:-1]
    mu = (11 / 14, 197 / 196, 1 / 8, 261 / 392)

    def rc(g):
        score = float(len(word))
        for i, m in enumerate(mu):
            if i + 1 < len(g):
                score += m * g[i + 1]
        return score

    return min(rc(g_exit), rc(g_near))


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    n = len(state)
    nz = sum(x == 0 for x in state)
    base_w = (0.0, 11 / 14, 197 / 196, 1 / 8, 261 / 392, 0.5, 0.5, 0.5)[:max(nz, 1)]
    weightings = [
        base_w,
        tuple(reversed(base_w)),
        base_w[1:] + base_w[:1],
        base_w[-1:] + base_w[:-1],
    ]
    incumbent = set()
    for cut in range(n):
        for prefer_right in (False, True):
            incumbent.add(_construct(state, cut, prefer_right))
    found = {}
    scales = (0.0, 0.35, 0.7, 1.5, 3.0)
    for cut in range(n):
        for prefer_right in (False, True):
            for scale in scales:
                for weights in weightings:
                    if scale == 0.0 and weights == base_w:
                        continue
                    word = _construct(state, cut, prefer_right, scale, weights)
                    if word not in incumbent and word not in found and len(word) <= 4096:
                        found[word] = _proxy(state, word)
            for at in range(0, 8):
                word = _construct(state, cut, prefer_right, 0.0, base_w, (at, 1))
                if word not in incumbent and word not in found and len(word) <= 4096:
                    found[word] = _proxy(state, word)
                word = _construct(state, cut, prefer_right, 1.5, base_w, (at, 1))
                if word not in incumbent and word not in found and len(word) <= 4096:
                    found[word] = _proxy(state, word)
    ranked = sorted(found, key=lambda w: (found[w], len(w), w))
    return ranked[:32]