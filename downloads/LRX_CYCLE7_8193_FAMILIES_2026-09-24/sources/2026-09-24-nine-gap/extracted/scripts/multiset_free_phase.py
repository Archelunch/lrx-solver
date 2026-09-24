"""Exact sorting with one forbidden physical X-edge and free terminal phase.

The cursor travels on the full circle. Greedy pruning makes the recurrence
acyclic. This is an upper bound on ordinary LRX distance, not its exact value.
Named values are 1..m, zeros are indistinguishable; the target is 1..m,0^r.
"""

from functools import cache


def circle(n, a, b):
    d = abs(a-b)
    return min(d, n-d)


@cache
def distances(q, end):
    """Tuple D(q,u,end), for all initial cursors u; q uses ranks 0..n-1."""
    n = len(q)
    assert sorted(q) == list(range(n)) and 0 <= end < n
    if all(q[i] < q[i+1] for i in range(n-1)):
        return tuple(circle(n, u, end) for u in range(n))
    choices = []
    for edge in range(n-1):
        if q[edge] > q[edge+1]:
            after = q[:edge]+(q[edge+1], q[edge])+q[edge+2:]
            choices.append((edge, 1+distances(after, end)[edge]))
    # Direct minimum: deliberately different from the C++ distance transform.
    return tuple(min(circle(n, u, edge)+cost for edge, cost in choices)
                 for u in range(n))


def stable_ranks(state, cut, end):
    """Unique noncrossing assignment of source zeros to target zero slots."""
    n = len(state)
    m = max(state, default=0)
    assert sorted(v for v in state if v) == list(range(1, m+1))
    zero_slots = iter(sorted((v+end) % n for v in range(m, n)))
    return tuple((v-1+end) % n if v else next(zero_slots)
                 for v in state[cut:]+state[:cut])


def best_chart(state):
    state = tuple(state)
    n = len(state)
    return min((distances(stable_ranks(state, cut, end), end)[(-cut) % n],
                cut, end)
               for cut in range(n) for end in range(n))


def rank_word(q, cursor, end):
    n = len(q)
    original, initial = q, cursor
    pieces = []

    def move(target):
        nonlocal cursor
        d = (target-cursor) % n
        pieces.append('L'*d if d <= n-d else 'R'*(n-d))
        cursor = target

    while any(q[i] > q[i+1] for i in range(n-1)):
        for edge in range(n-1):
            if q[edge] <= q[edge+1]:
                continue
            after = q[:edge]+(q[edge+1], q[edge])+q[edge+2:]
            if circle(n, cursor, edge)+1+distances(after, end)[edge] != distances(q, end)[cursor]:
                continue
            move(edge)
            pieces.append('X')
            q = after
            break
        else:
            raise AssertionError('Missing minimizing descent')
    move(end)
    result = ''.join(pieces)
    assert len(result) == distances(original, end)[initial]
    return result


def replay(state, word):
    """Replay visible L/R rotations, independently of the fixed chart."""
    a = list(state)
    for letter in word:
        if letter == 'L':
            a = a[1:]+a[:1]
        elif letter == 'R':
            a = a[-1:]+a[:-1]
        else:
            assert letter == 'X'
            a[0], a[1] = a[1], a[0]
    return tuple(a)


def word(state):
    state = tuple(state)
    n, m = len(state), max(state, default=0)
    cost, cut, end = best_chart(state)
    result = rank_word(stable_ranks(state, cut, end), (-cut) % n, end)
    assert len(result) == cost
    assert replay(state, result) == tuple(range(1, m+1))+(0,)*(n-m)
    cursor = 0
    for letter in result:
        if letter == 'X':
            assert cursor != (cut-1) % n
        else:
            cursor = (cursor+(1 if letter == 'L' else -1)) % n
    assert cursor == (cut+end) % n
    return result
