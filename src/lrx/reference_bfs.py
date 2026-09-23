"""Independent exact BFS with marked-zero states and budget tracking.

Computes true shortest distances and marks COMPLETE/INCOMPLETE results
based on resource constraints. No DP or canonicalization tricks—literal
tuple states and BFS traversal.
"""

from collections import deque
from typing import Tuple, Dict, Optional
import sys

from .state import (
    canonical_root,
    smaller_root,
    apply_marked_L,
    apply_marked_R,
    apply_marked_X,
    apply_L,
    apply_R,
    apply_X,
    validate_parameters,
)


class BFSResult:
    """Result of BFS computation with status tracking."""

    def __init__(self):
        self.distances: Dict[Tuple[Tuple[int, ...], int], int] = {}
        self.parent: Dict[
            Tuple[Tuple[int, ...], int], Tuple[Tuple[Tuple[int, ...], int], str]
        ] = {}
        self.status = "COMPLETE"  # or "INCOMPLETE"
        self.exhaustion_reason = None
        self.max_queue_size = 0
        self.vertices_explored = 0
        self.memory_mb = 0

    def distance(self, state: Tuple[Tuple[int, ...], int]) -> Optional[int]:
        """Return exact distance or None if not computed."""
        return self.distances.get(state)

    def path(self, state: Tuple[Tuple[int, ...], int]) -> Optional[str]:
        """Reconstruct word from root to state, if computed."""
        if state not in self.distances:
            return None
        word = []
        current = state
        while current in self.parent:
            prev, op = self.parent[current]
            word.append(op)
            current = prev
        return "".join(reversed(word))


def bfs_marked_zero(
    m: int,
    r: int,
    max_vertices: int = 1_000_000,
    max_queue_size: int = 500_000,
    verbose: bool = False,
) -> BFSResult:
    """
    Exact BFS in marked-zero graph.

    Args:
        m: size parameter (number of non-zero elements in root)
        r: number of zeros in canonical root
        max_vertices: stop if vertices_explored exceeds this
        max_queue_size: stop if queue size exceeds this
        verbose: print progress

    Returns:
        BFSResult with distances, parent pointers, status, and diagnostics.
    """
    validate_parameters(m, r)
    if r < 1 or max_vertices < 1 or max_queue_size < 1:
        raise ValueError("Positive zero count and resource limits required")
    result = BFSResult()
    root = (
        smaller_root(m, r),
        m,
    )  # Start state: smaller root, marked zero at position m
    queue = deque([root])
    result.distances[root] = 0
    result.vertices_explored = 0

    while queue:
        if len(queue) > result.max_queue_size:
            result.max_queue_size = len(queue)
        if result.vertices_explored >= max_vertices:
            result.status = "INCOMPLETE"
            result.exhaustion_reason = (
                f"Explored {result.vertices_explored} vertices, hit limit"
            )
            break
        if len(queue) > max_queue_size:
            result.status = "INCOMPLETE"
            result.exhaustion_reason = (
                f"Queue size {len(queue)} exceeded limit {max_queue_size}"
            )
            break

        current = queue.popleft()
        current_dist = result.distances[current]
        result.vertices_explored += 1

        if verbose and result.vertices_explored % 10000 == 0:
            print(
                f"BFS progress: {result.vertices_explored} vertices, "
                f"queue size {len(queue)}, distance {current_dist}",
                file=sys.stderr,
            )

        # Expand: try L, R, X
        for next_state, op in [
            (apply_marked_L(current), "L"),
            (apply_marked_R(current), "R"),
            (apply_marked_X(current), "X"),
        ]:
            if next_state not in result.distances:
                if (
                    len(result.distances) >= max_vertices
                    or len(queue) >= max_queue_size
                ):
                    result.status = "INCOMPLETE"
                    result.exhaustion_reason = "Discovered-state or queue limit reached"
                    return result
                result.distances[next_state] = current_dist + 1
                result.parent[next_state] = (current, op)
                queue.append(next_state)

    return result


def bfs_visible(m, r, max_vertices=100_000):
    """Canonical-root distances on visible vectors, not distinguished-zero states."""
    validate_parameters(m, r)
    if type(max_vertices) is not int or max_vertices < 1:
        raise ValueError("max_vertices must be a positive integer")
    result = BFSResult()
    root = canonical_root(m, r)
    result.distances[root] = 0
    queue = deque([root])
    while queue:
        result.max_queue_size = max(result.max_queue_size, len(queue))
        u = queue.popleft()
        result.vertices_explored += 1
        for op, move in (("L", apply_L), ("R", apply_R), ("X", apply_X)):
            v = move(u)
            if v not in result.distances:
                if len(result.distances) >= max_vertices:
                    result.status = "INCOMPLETE"
                    result.exhaustion_reason = "Discovered-state limit reached"
                    return result
                result.distances[v] = result.distances[u] + 1
                result.parent[v] = u, op
                queue.append(v)
    return result


def bfs_distance(
    m: int, r: int, target_state: Tuple[Tuple[int, ...], int], **kwargs
) -> Optional[int]:
    """Quick helper: return distance to a specific marked-zero state."""
    result = bfs_marked_zero(m, r, **kwargs)
    return result.distance(target_state)


def bfs_from_vector(
    m: int, r: int, target_vector: Tuple[int, ...], j: int, **kwargs
) -> Tuple[Optional[int], str]:
    """
    Compute exact distance from canonical root to marked-zero state derived from a vector.

    Args:
        m, r: parameters
        target_vector: visible vector (with marked zero at some position)
        j: position of marked zero in target_vector

    Returns:
        (distance, status_string)
    """
    # Remove marked zero to get state
    u = target_vector[:j] + target_vector[j + 1 :]
    target_state = (u, j)

    result = bfs_marked_zero(m, r, **kwargs)
    dist = result.distance(target_state)

    if result.status == "INCOMPLETE":
        status = f"INCOMPLETE ({result.exhaustion_reason})"
    elif dist is None:
        status = "UNREACHABLE"
    else:
        status = "COMPLETE"

    return dist, status
