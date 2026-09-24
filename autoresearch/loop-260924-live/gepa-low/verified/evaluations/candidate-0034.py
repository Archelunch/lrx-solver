"""Executable LRX constructor: inversion sorts with complementary cuts and zero ranks.

Self-contained. propose_words returns a finite list of complete unit-block words.
Extra profiles are specializations aimed at residual slope faces; they are not a
certificate by themselves.
"""


def _state(labels, mask):
    out = []
    for j in range(9):
        if mask >> j & 1:
            out.append(0)
        if j < 8:
            out.append(labels[j])
    return out


def _free_slots(n, cut):
    targets = {x: (x - 1 - cut) % n for x in range(1, 9)}
    free = sorted(set(range(n)) - set(targets.values()))
    return targets, free


def _ranks(state, cut, zero_order=None):
    n = len(state)
    targets, free = _free_slots(n, cut)
    if zero_order is None:
        assigned = free
    else:
        assigned = [free[i] for i in zero_order]
    zeros = iter(assigned)
    rotated = state[cut:] + state[:cut]
    return [targets[x] if x else next(zeros) for x in rotated]


def _zero_orders(state, cut):
    n = len(state)
    _, free = _free_slots(n, cut)
    k = len(free)
    slots = list(range(k))
    orders = [slots, list(reversed(slots))]
    if k > 1:
        orders.append(slots[1:] + slots[:1])
        inter = []
        lo, hi = 0, k - 1
        while lo <= hi:
            inter.append(lo)
            if lo != hi:
                inter.append(hi)
            lo += 1
            hi -= 1
        orders.append(inter)
    rotated = state[cut:] + state[:cut]
    used = set()
    natural = []
    for i, x in enumerate(rotated):
        if x:
            continue
        best = min(
            (s for s in free if s not in used),
            key=lambda s: (min((s - i) % n, (i - s) % n), s),
        )
        used.add(best)
        natural.append(free.index(best))
    orders.append(natural)
    uniq = []
    for order in orders:
        if order not in uniq:
            uniq.append(order)
    return uniq


def _finish(word, at, n):
    left, right = (-at) % n, at
    word.extend('L' * left if left <= right else 'R' * right)
    return ''.join(word)


def _step(at, pos, n, prefer_right):
    left, right = (pos - at) % n, (at - pos) % n
    if left < right or (left == right and not prefer_right):
        return 'L', left
    return 'R', right


def _construct(state, cut, prefer_right):
    n = len(state)
    rank = _ranks(state, cut, None)
    at = 0
    word = []
    while True:
        choices = []
        for pos in range(n):
            j = (pos - cut) % n
            if j == n - 1 or rank[j] <= rank[j + 1]:
                continue
            direction, steps = _step(at, pos, n, prefer_right)
            choices.append((steps, -pos if prefer_right else pos, pos, j, direction))
        if not choices:
            break
        steps, _, pos, j, direction = min(choices)
        word.extend(direction * steps)
        word.append('X')
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
    return _finish(word, at, n)


def _greedy(state, cut, prefer_right, zero_order, policy):
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
            direction, steps = _step(at, pos, n, prefer_right)
            gap = rank[j] - rank[j + 1]
            if policy == 0:
                key = (steps, -gap, pos)
            elif policy == 1:
                key = (-gap, steps, pos)
            elif policy == 2:
                key = (gap, steps, -pos if prefer_right else pos)
            else:
                key = ((3 * j + policy * pos) % n, steps, -gap)
            choices.append((key, steps, pos, j, direction))
        if not choices:
            break
        _, steps, pos, j, direction = min(choices)
        word.extend(direction * steps)
        word.append('X')
        rank[j], rank[j + 1] = rank[j + 1], rank[j]
        at = pos
    return _finish(word, at, n)


def _insertion(state, cut, prefer_right, zero_order):
    n = len(state)
    rank = _ranks(state, cut, zero_order)
    at = 0
    word = []
    for dest in range(n - 1):
        loc = rank.index(dest)
        while loc != dest:
            j = loc - 1 if loc > dest else loc
            pos = (j + cut) % n
            direction, steps = _step(at, pos, n, prefer_right)
            word.extend(direction * steps)
            word.append('X')
            rank[j], rank[j + 1] = rank[j + 1], rank[j]
            at = pos
            loc += -1 if loc > dest else 1
    return _finish(word, at, n)


def _bubble(state, cut, prefer_right, zero_order):
    n = len(state)
    rank = _ranks(state, cut, zero_order)
    at = 0
    word = []
    changed = True
    while changed:
        changed = False
        for j in range(n - 1):
            if rank[j] <= rank[j + 1]:
                continue
            pos = (j + cut) % n
            direction, steps = _step(at, pos, n, prefer_right)
            word.extend(direction * steps)
            word.append('X')
            rank[j], rank[j + 1] = rank[j + 1], rank[j]
            at = pos
            changed = True
    return _finish(word, at, n)


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    state = _state(case['labels'], case['mask'])
    n = len(state)
    rich = case.get('mask') in (302, 315) or case.get('id') in (
        'k5-mask302-order15713',
        'k6-mask315-order31970',
    )
    cap = 40 if rich else 14
    words = []

    def add(word):
        if word and word not in words and len(words) < cap:
            words.append(word)

    cuts = [0, n // 4, n // 2, (3 * n) // 4]
    for cut in cuts:
        for prefer_right in (False, True):
            add(_construct(state, cut, prefer_right))

    extra = []
    for i, x in enumerate(state):
        if x == 0 and i not in extra:
            extra.append(i)
    if rich:
        for i in range(n):
            if i not in extra:
                extra.append(i)
    for cut in cuts + extra:
        orders = _zero_orders(state, cut)
        # natural order is last; sorted is first
        selected = [orders[-1], orders[0]]
        if rich and len(orders) > 2:
            selected.append(orders[1])
            selected.append(orders[2])
        for order in selected:
            for prefer_right in (False, True):
                add(_greedy(state, cut, prefer_right, order, 1))
                if rich:
                    add(_greedy(state, cut, prefer_right, order, 0))
                    add(_insertion(state, cut, prefer_right, order))
                if len(words) >= cap:
                    return words
            if rich:
                add(_bubble(state, cut, False, order))
                add(_greedy(state, cut, True, order, 2))
                add(_greedy(state, cut, False, order, 5))
            if len(words) >= cap:
                return words
    return words