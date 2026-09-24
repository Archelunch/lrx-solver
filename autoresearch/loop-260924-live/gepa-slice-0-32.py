# Post-hoc cap repair of original SHA-256 4fc49ae8d742e6118602f1e9a08ea66f70a3a598a5ae245a7cbcf56175419499; slice 0:32.
"""Unit-block LRX words: seed cuts plus direction, order, and zero-avoidance variants.

Self-contained constructor. Extra words are complete adjacent-inversion sorts
with complementary travel, not distance claims.
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


def _construct(state, cut, prefer_right, mode="short", policy="seed", avoid=(), weight=4):
    n = len(state)
    rank = _ranks(state, cut)
    at = 0
    word = []
    blocked = set(avoid)
    phase = 0
    for _ in range(n * n + 2):
        inversions = [j for j in range(n - 1) if rank[j] > rank[j + 1]]
        if not inversions:
            break
        pool = inversions
        if policy == "oddeven":
            odd = [j for j in inversions if (j & 1) == phase]
            if odd:
                pool = odd
            phase ^= 1
        choices = []
        for j in pool:
            pos = (j + cut) % n
            left, right = (pos - at) % n, (at - pos) % n
            if mode == "L":
                direction, steps = "L", left
            elif mode == "R":
                direction, steps = "R", right
            elif mode == "long":
                if left > right or (left == right and prefer_right):
                    direction, steps = "L", left
                else:
                    direction, steps = "R", right
            else:
                if left < right or (left == right and not prefer_right):
                    direction, steps = "L", left
                else:
                    direction, steps = "R", right
            if direction == "L":
                arc = ((at + t) % n for t in range(steps))
            else:
                arc = ((at - t) % n for t in range(steps))
            pen = sum(1 for z in arc if z in blocked)
            span = rank[j] - rank[j + 1]
            tie = -pos if prefer_right else pos
            cost = steps + weight * pen
            if policy == "bubble":
                key = (j, cost, tie)
            elif policy == "cobubble":
                key = (-j, cost, tie)
            elif policy == "steep":
                key = (-span, cost, tie)
            else:
                key = (cost, tie, j)
            choices.append((key, steps, pos, j, direction))
        if not choices:
            break
        _, steps, pos, j, direction = min(choices)
        if len(word) + steps + 1 > 340:
            return None
        word.extend(direction * steps)
        word.append("X")
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
    else:
        return None
    if any(rank[j] > rank[j + 1] for j in range(n - 1)):
        return None
    left, right = (-at) % n, at
    word.extend("L" * left if left <= right else "R" * right)
    return "".join(word)


def _unbounded_words(case):
    if case["m"] != 8:
        raise ValueError("m=8 only")
    state = _state(case["labels"], case["mask"])
    n = len(state)
    zeros = [i for i, x in enumerate(state) if x == 0]
    words = []
    seen = set()

    def add(word):
        if word and word not in seen and len(words) < 56:
            seen.add(word)
            words.append(word)

    for cut in (0, n // 4, n // 2, 3 * n // 4):
        for prefer_right in (False, True):
            add(_construct(state, cut, prefer_right))

    specs = []
    for cut in range(n):
        for prefer_right in (False, True):
            specs.append((cut, prefer_right, "short", "seed", (), 0))
            specs.append((cut, prefer_right, "short", "bubble", (), 0))
            specs.append((cut, prefer_right, "short", "cobubble", (), 0))
            specs.append((cut, prefer_right, "short", "steep", (), 0))
            specs.append((cut, prefer_right, "short", "oddeven", (), 0))
            specs.append((cut, prefer_right, "L", "seed", (), 0))
            specs.append((cut, prefer_right, "R", "bubble", (), 0))
            specs.append((cut, prefer_right, "long", "seed", (), 0))
            for z in zeros:
                specs.append((cut, prefer_right, "short", "seed", (z,), 3))
                specs.append((cut, prefer_right, "short", "steep", (z,), 8))
            if len(zeros) >= 2:
                specs.append((cut, prefer_right, "short", "seed", tuple(zeros[1:]), 4))
                specs.append((cut, prefer_right, "L", "bubble", tuple(zeros[:-1]), 5))
    buckets = [[] for _ in range(10)]
    for i, spec in enumerate(specs):
        buckets[i % 10].append(spec)
    idx = 0
    progressed = True
    while len(words) < 56 and progressed:
        progressed = False
        for bucket in buckets:
            if idx < len(bucket):
                cut, prefer_right, mode, policy, avoid, weight = bucket[idx]
                add(_construct(state, cut, prefer_right, mode, policy, avoid, weight))
                progressed = True
                if len(words) >= 56:
                    break
        idx += 1
    return words

def propose_words(case):
    return _unbounded_words(case)[0:32]
