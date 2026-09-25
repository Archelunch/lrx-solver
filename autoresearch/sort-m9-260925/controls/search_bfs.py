"""Exploit probe (not a control): plain BFS from v to the root over L, R, X.

Optimal whenever it finishes. Used only to show that sort-contract-2's 0.2 s CPU
limit per state makes state-space search time out on almost every state.
"""
from collections import deque


def sort_word(v):
    m = max(v)
    goal = tuple(range(1, m + 1)) + (0,) * (len(v) - m)
    start = tuple(v)
    parent = {start: None}
    queue = deque([start])
    while queue:
        u = queue.popleft()
        if u == goal:
            word = []
            while parent[u] is not None:
                u, ch = parent[u]
                word.append(ch)
            return ''.join(reversed(word))
        for ch, w in (('L', u[1:] + u[:1]), ('R', u[-1:] + u[:-1]), ('X', (u[1], u[0]) + u[2:])):
            if w not in parent:
                parent[w] = (u, ch)
                queue.append(w)
    return ''
