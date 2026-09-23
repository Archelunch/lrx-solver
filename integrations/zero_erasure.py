"""Linear-time projection counts for every labelled zero of a fixed LRX word.

Search-side helper only. Positive witnesses still go through the trusted
CertificateValidator. See the session-05 proof note for the counting identity.
"""
from collections import deque

from src.lrx.state import canonical_root, validate_vector


def count_projections(v, m, r, word):
    v = tuple(v)
    validate_vector(v, m, r)
    if m < 2 or r < 1:
        raise ValueError("counting identity requires m >= 2 and r >= 1")
    if not isinstance(word, str) or any(letter not in "LRX" for letter in word):
        raise ValueError("word must contain only L, R, X")
    positions = [j for j, token in enumerate(v) if token == 0]
    labels = iter(range(-1, -r - 1, -1))
    state = deque(token if token else next(labels) for token in v)
    individual = [0] * r
    idle = 0
    for letter in word:
        if letter == "L":
            token = state.popleft()
            state.append(token)
            if token < 0:
                individual[-token - 1] += 1
        elif letter == "R":
            token = state.pop()
            state.appendleft(token)
            if token < 0:
                individual[-token - 1] += 1
        else:
            a, b = state[0], state[1]
            if a < 0 and b < 0:
                idle += 1
            elif min(a, b) < 0:
                individual[-min(a, b) - 1] += 1
            state[0], state[1] = b, a
    final = tuple(max(0, token) for token in state)
    return {"length": len(word), "idle_zero_swaps": idle,
            "zero_events": sum(individual), "final_vector": final,
            "terminal": final == canonical_root(m, r),
            "deletions": [{"j": j, "individual_erasures": count,
                           "projection_length": len(word) - idle - count}
                          for j, count in zip(positions, individual)]}
