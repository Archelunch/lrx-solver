"""Bounded exact recurrences; infinity means mathematical infeasibility only."""

from math import inf

from .reference_bfs import bfs_visible
from .state import (
    apply_L,
    apply_R,
    apply_X,
    smaller_root,
    state_counts,
    validate_vector,
)


class ResourceLimit(RuntimeError):
    """The computation was refused or incomplete, not mathematically infeasible."""


def three_vertex_distance(j, k, n):
    if j == k:
        return 0
    if j not in (0, 1, n - 1) or k not in (0, 1, n - 1):
        return None
    return 1 if 0 in (j, k) else 2


def compute_marked_transitions(u, j, n):
    return {
        "L": (u, n - 1) if j == 0 else (apply_L(u), j - 1),
        "R": (u, 0) if j == n - 1 else (apply_R(u), j + 1),
        "X": (u, 1 - j) if j < 2 else (apply_X(u), j),
    }


def _closure(values):
    result = values.copy()
    n = len(values)
    for j in (0, 1, n - 1):
        result[j] = min(
            values[k] + three_vertex_distance(j, k, n) for k in (0, 1, n - 1)
        )
    return result


class _Base:
    def __init__(self, m, r, max_memo=1_000_000, max_q=100):
        if m < 2 or r < 2:
            raise ValueError("Projection DP requires m >= 2 and r >= 2")
        self.root = smaller_root(m, r)
        self.m, self.r, self.n = m, r, m + r
        if (
            type(max_memo) is not int
            or max_memo < 1
            or type(max_q) is not int
            or max_q < 0
        ):
            raise ValueError("Invalid resource limit")
        self.max_memo, self.max_q = max_memo, max_q
        self.counts = state_counts(m, r)
        self.layers = []
        self.incomplete = False
        self._preflight(0)

    def _preflight(self, budget):
        cells = self.counts["marked"] * (budget + 1)
        if budget > self.max_q or cells > self.max_memo or cells * 12 > 30_000_000:
            self.incomplete = True
            raise ResourceLimit(
                f"Refused {cells} DP cells (limit {self.max_memo}, budget {budget})"
            )

    def _query(self, budget, u, j):
        if type(budget) is not int or budget < 0:
            raise ValueError("Budget must be a nonnegative integer")
        validate_vector(u, self.m, self.r - 1)
        if type(j) is not int or not 0 <= j < self.n:
            raise ValueError("Invalid marked position")
        self._preflight(budget)

    def _initial(self, u):
        return [0 if u == self.root and j >= self.m else inf for j in range(self.n)]


class ExactHqDp(_Base):
    """Absolute projection-budget DP, retaining bounded layers for comparison."""

    def __init__(self, m, r, max_memo=1_000_000, max_q=100):
        super().__init__(m, r, max_memo, max_q)
        # BFS is used only to enumerate u; its distances are not used by this DP.
        result = bfs_visible(m, r - 1, max_vertices=self.counts["smaller"])
        if result.status != "COMPLETE":
            raise ResourceLimit("Smaller graph enumeration incomplete")
        self.states = tuple(result.distances)

    def compute_H_q(self, q, u, j):
        self._query(q, u, j)
        while len(self.layers) <= q:
            previous = self.layers[-1] if self.layers else None
            layer = {}
            for state in self.states:
                values = self._initial(state)
                if previous is not None:
                    for pos in range(self.n):
                        for target, target_pos in compute_marked_transitions(
                            state, pos, self.n
                        ).values():
                            if target != state:
                                values[pos] = min(
                                    values[pos], 1 + previous[target][target_pos]
                                )
                layer[state] = _closure(values)
            self.layers.append(layer)
        return self.layers[q][u][j]

    def witness(self, q, u, j):
        """Reconstruct a word; callers must replay it independently."""
        remaining = self.compute_H_q(q, u, j)
        if remaining == inf:
            return None
        word = []
        while remaining:
            for op, (target, pos) in compute_marked_transitions(u, j, self.n).items():
                next_q = q - int(target != u)
                if next_q >= 0 and self.layers[next_q][target][pos] == remaining - 1:
                    word.append(op)
                    u, j, q = target, pos, next_q
                    remaining -= 1
                    break
            else:
                raise AssertionError("DP has no reconstructible witness")
        return "".join(word)


class ExactFeDp(_Base):
    """Excess-budget DP ordered by (e, smaller distance), with a certified oracle."""

    def __init__(self, m, r, distances, max_memo=1_000_000, max_q=100):
        super().__init__(m, r, max_memo, max_q)
        self.distances = dict(distances)
        if len(distances) != self.counts["smaller"] or distances.get(self.root) != 0:
            raise ValueError(
                "A complete exact smaller-graph distance oracle is required"
            )
        for u, d in distances.items():
            validate_vector(u, m, r - 1)
            if type(d) is not int or d < 0 or (d == 0 and u != self.root):
                raise ValueError("Invalid distance oracle")
            neighbours = (apply_L(u), apply_R(u), apply_X(u))
            if any(v not in distances for v in neighbours):
                raise ValueError("Distance oracle is not closed")
            if u != self.root and d != 1 + min(distances[v] for v in neighbours):
                raise ValueError("Distance oracle fails Bellman equations")
        self.states = sorted(distances, key=distances.get)

    def compute_F_e(self, e, u, j):
        self._query(e, u, j)
        while len(self.layers) <= e:
            excess = len(self.layers)
            layer = {}
            for state in self.states:
                values = self._initial(state)
                for pos in range(self.n):
                    for target, target_pos in compute_marked_transitions(
                        state, pos, self.n
                    ).values():
                        if target == state:
                            continue
                        cost = 1 + self.distances[target] - self.distances[state]
                        if cost <= excess:
                            source = layer if cost == 0 else self.layers[excess - cost]
                            values[pos] = min(
                                values[pos], 1 + source[target][target_pos]
                            )
                layer[state] = _closure(values)
            self.layers.append(layer)
        return self.layers[e][u][j]
