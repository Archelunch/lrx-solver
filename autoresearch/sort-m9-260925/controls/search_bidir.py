"""Exploit probe (not a control): meet-in-the-middle search with a root ball built lazily
and cached across calls, plus a forward BFS from v. Optimal whenever it finishes.
Used only to show that sort-contract-2's CPU limits defeat search that amortizes work
across states of a batch.
"""
BALL = {}


def _moves(u):
    return (('L', u[1:] + u[:1], 'R'), ('R', u[-1:] + u[:-1], 'L'), ('X', (u[1], u[0]) + u[2:], 'X'))


def _grow(goal, depth):
    ball = BALL.setdefault(goal, {goal: ''})
    frontier = [u for u, w in ball.items() if len(w) == max(len(x) for x in ball.values())]
    for _ in range(depth):
        nxt = []
        for u in frontier:
            for _, w, inv in _moves(u):
                if w not in ball:
                    ball[w] = inv + ball[u]  # word from w to goal
                    nxt.append(w)
        frontier = nxt
    return ball


def sort_word(v):
    m = max(v)
    goal = tuple(range(1, m + 1)) + (0,) * (len(v) - m)
    ball = _grow(goal, 1)
    start = tuple(v)
    seen = {start: ''}
    frontier = [start]
    while frontier:
        for u in frontier:
            if u in ball:
                return seen[u] + ball[u]
        nxt = []
        for u in frontier:
            for ch, w, _ in _moves(u):
                if w not in seen:
                    seen[w] = seen[u] + ch
                    nxt.append(w)
        frontier = nxt
    return ''
