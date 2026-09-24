"""One Sol-authored column-generation step, independent of model output.

Beam-search complete adjacent-inversion words.  The frozen k5 dual weights
rank partial resource cost; the trusted evaluator independently checks every
returned word and recomputes exact profiles and mixtures.  Other cases return
an empty list and retain their frozen incumbent pools.
"""


def _state(labels, mask):
    state = []
    for j in range(9):
        if mask >> j & 1:
            state.append(0)
        if j < 8:
            state.append(labels[j])
    return state


def _one_cut(state, cut):
    n = len(state)
    named_targets = {value: (value - 1 - cut) % n for value in range(1, 9)}
    zero_targets = iter(sorted(set(range(n)) - set(named_targets.values())))
    zero_ids = iter(range(n - 8))
    original_ids = [next(zero_ids) if value == 0 else -1 for value in state]
    ordered = state[cut:] + state[:cut]
    ordered_ids = original_ids[cut:] + original_ids[:cut]
    ranks = []
    zero_of_rank = [-1] * n
    for value, zero_id in zip(ordered, ordered_ids):
        rank = named_targets[value] if value else next(zero_targets)
        ranks.append(rank)
        if zero_id >= 0:
            zero_of_rank[rank] = zero_id
    # 20 times the verified 59-column dual multipliers for gamma[0:5].
    multiplier = (0, 44, 10, 19, 15)
    initial = (0, tuple(ranks), 0, (0,) * (n - 8 + 1), '')
    beam = [initial]  # (weighted partial cost, ranks, head, unfinished gap, word)
    inversions = sum(ranks[i] > ranks[j] for i in range(n) for j in range(i + 1, n))

    def rotations(ranks, at, gap, pos, direction):
        steps = (pos - at) % n if direction == 'L' else (at - pos) % n
        sign = 1 if direction == 'L' else -1
        changed = list(gap)
        changed[0] += sign * steps
        for step in range(steps):
            physical = ((at + step) % n if direction == 'L'
                        else (at - step - 1) % n)
            zero = zero_of_rank[ranks[(physical - cut) % n]]
            if zero >= 0:
                changed[zero + 1] += sign
        return steps, changed

    for _ in range(inversions):
        next_nodes = {}
        for cost, ranks, at, gap, word in beam:
            for j in range(n - 1):
                if ranks[j] <= ranks[j + 1]:
                    continue
                pos = (j + cut) % n
                left_zero = zero_of_rank[ranks[j]]
                right_zero = zero_of_rank[ranks[j + 1]]
                for direction in ('L', 'R'):
                    steps, changed = rotations(ranks, at, gap, pos, direction)
                    if left_zero >= 0:
                        changed[left_zero + 1] += 1
                    delta = 20 * (1 + abs(changed[0]))
                    delta += sum(weight * abs(changed[z + 1])
                                 for z, weight in enumerate(multiplier))
                    if left_zero >= 0:
                        delta += 2 * multiplier[left_zero]
                    elif right_zero >= 0:
                        delta += 2 * multiplier[right_zero]
                    after_gap = [0] * len(gap)
                    if right_zero >= 0:
                        after_gap[right_zero + 1] = -1
                    after_ranks = list(ranks)
                    after_ranks[j], after_ranks[j + 1] = after_ranks[j + 1], after_ranks[j]
                    key = (tuple(after_ranks), pos, tuple(after_gap))
                    new_cost = cost + delta
                    candidate = (new_cost, key[0], pos, key[2], word + direction * steps + 'X')
                    previous = next_nodes.get(key)
                    if previous is None or (new_cost, candidate[4]) < (previous[0], previous[4]):
                        next_nodes[key] = candidate
        if not next_nodes:
            return []
        # The remaining inversion count is identical across each layer.  A
        # one-step travel lower bound breaks ties before the beam is trimmed.
        def priority(node):
            cost, ranks, at, _, word = node
            distance = min((min((j + cut - at) % n, (at - j - cut) % n)
                            for j in range(n - 1) if ranks[j] > ranks[j + 1]),
                           default=0)
            return (cost + 20 * distance, cost, len(word), word)
        beam = sorted(next_nodes.values(), key=priority)[:64]

    complete = []
    for cost, ranks, at, gap, word in beam:
        if ranks != tuple(range(n)):
            continue
        for direction in ('L', 'R'):
            steps, changed = rotations(ranks, at, gap, 0, direction)
            final_cost = cost + 20 * abs(changed[0])
            final_cost += sum(weight * abs(changed[z + 1])
                              for z, weight in enumerate(multiplier))
            complete.append((final_cost, word + direction * steps))
    unique = {}
    for cost, word in complete:
        unique[word] = min(cost, unique.get(word, cost))
    return [(cost, word) for word, cost in
            sorted(unique.items(), key=lambda item: (item[1], item[0]))[:8]]


def propose_words(case):
    if case['m'] != 8:
        raise ValueError('m=8 only')
    if case['mask'] != 302 or case['labels'] != [4, 1, 7, 8, 5, 6, 3, 2]:
        return []
    state = _state(case['labels'], case['mask'])
    ranked = []
    for cut in range(len(state)):
        ranked.extend((cost, cut, word) for cost, word in _one_cut(state, cut))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    # Keep the previously verified negative-reduced-cost word, even if the
    # wider beam prunes its construction path at a later layer.
    prior_witness = 'XLXRRRXRXLXLXLXRRXRRRXRRXRXLXLXRXRRXLXRRRXRXRXRXLX'
    words = [prior_witness]
    seen = {prior_witness}
    # One lowest-cost completion per cut before filling by global cost.
    for cut in range(len(state)):
        for _, source_cut, word in ranked:
            if source_cut == cut and word not in seen:
                words.append(word)
                seen.add(word)
                break
    for _, _, word in ranked:
        if len(words) >= 32:
            break
        if word not in seen:
            words.append(word)
            seen.add(word)
    return words[:32]
