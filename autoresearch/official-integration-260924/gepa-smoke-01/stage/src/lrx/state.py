"""Tuple state operations for marked-zero LRX system.

State: (u, j) where u is a tuple of length n-1 (vector with marked zero removed)
and j ∈ {0,...,n-1} is the insertion position of the marked zero.
Root: (1,...,m,0,...,0) with m+r elements, r zeros.
Smaller root: (1,...,m,0,...,0) with m+r-1 elements, r-1 zeros.
"""

from typing import Tuple
import math


def validate_parameters(m: int, r: int) -> None:
    if type(m) is not int or type(r) is not int or m < 1 or r < 0 or m + r > 10000:
        raise ValueError("Require integer m >= 1, r >= 0, n <= 10000")


def validate_vector(v: Tuple[int, ...], m: int, r: int) -> None:
    validate_parameters(m, r)
    if not isinstance(v, tuple) or any(type(x) is not int for x in v):
        raise ValueError("Vector must be a tuple of integers")
    if sorted(v) != sorted(canonical_root(m, r)):
        raise ValueError("Vector does not match the specified multiset")


def state_counts(m: int, r: int) -> dict:
    validate_parameters(m, r)
    n = m + r
    visible = math.prod(range(r + 1, n + 1))
    return {"visible": visible, "smaller": visible * r // n, "marked": visible * r}


def canonical_root(m: int, r: int) -> Tuple[int, ...]:
    """Return the visible canonical root (1,...,m,0^r) with n=m+r elements."""
    validate_parameters(m, r)
    return tuple(range(1, m + 1)) + (0,) * r


def smaller_root(m: int, r: int) -> Tuple[int, ...]:
    """Return the smaller root (1,...,m,0^(r-1)) with n-1=m+r-1 elements."""
    validate_parameters(m, r)
    if r < 1:
        raise ValueError("r must be >= 1")
    return tuple(range(1, m + 1)) + (0,) * (r - 1)


def insert_zero(u: Tuple[int, ...], j: int) -> Tuple[int, ...]:
    """Insert a marked zero (represented as 0) at position j into vector u."""
    if type(j) is not int or not 0 <= j <= len(u):
        raise ValueError("Invalid insertion position")
    return u[:j] + (0,) + u[j:]


def remove_zero_at(v: Tuple[int, ...], j: int) -> Tuple[int, ...]:
    """Remove zero at position j from vector v. Assumes v[j] == 0."""
    if type(j) is not int or not 0 <= j < len(v) or v[j] != 0:
        raise ValueError("Position must contain a zero")
    return v[:j] + v[j + 1 :]


def apply_L(u: Tuple[int, ...]) -> Tuple[int, ...]:
    """Apply cyclic left rotation: move first element to end."""
    if len(u) == 0:
        return u
    return u[1:] + (u[0],)


def apply_R(u: Tuple[int, ...]) -> Tuple[int, ...]:
    """Apply cyclic right rotation: move last element to start."""
    if len(u) == 0:
        return u
    return (u[-1],) + u[:-1]


def apply_X(u: Tuple[int, ...]) -> Tuple[int, ...]:
    """Apply swap of first two elements."""
    if len(u) < 2:
        return u
    return (u[1], u[0]) + u[2:]


def apply_marked_L(state: Tuple[Tuple[int, ...], int]) -> Tuple[Tuple[int, ...], int]:
    """Apply L to marked-zero state (u, j).

    L: if j=0 -> (u, n-1), else (Lu, j-1)
    """
    u, j = state
    n = len(u) + 1  # Length including the marked zero
    if j == 0:
        return (u, n - 1)
    else:
        return (apply_L(u), j - 1)


def apply_marked_R(state: Tuple[Tuple[int, ...], int]) -> Tuple[Tuple[int, ...], int]:
    """Apply R to marked-zero state (u, j).

    R: if j=n-1 -> (u, 0), else (Ru, j+1)
    """
    u, j = state
    n = len(u) + 1
    if j == n - 1:
        return (u, 0)
    else:
        return (apply_R(u), j + 1)


def apply_marked_X(state: Tuple[Tuple[int, ...], int]) -> Tuple[Tuple[int, ...], int]:
    """Apply X to marked-zero state (u, j).

    X: if j in {0,1} -> (u, 1-j), else (Xu, j)

    Special case: if Xu == u, this is a self-loop (omittable).
    """
    u, j = state
    if j == 0 or j == 1:
        return (u, 1 - j)
    else:
        new_u = apply_X(u)
        if new_u == u:
            # Self-loop: can be omitted
            return (u, j)
        return (new_u, j)


def is_terminal(state: Tuple[Tuple[int, ...], int], m: int, r: int) -> bool:
    """Check if state is terminal: u is the smaller root and j >= m."""
    u, j = state
    expected_u = smaller_root(m, r)
    return u == expected_u and m <= j < m + r


def state_from_vector(v: Tuple[int, ...], j: int) -> Tuple[Tuple[int, ...], int]:
    """Convert a vector v with marked zero at position j to state (u, j)."""
    return (remove_zero_at(v, j), j)


def vector_from_state(state: Tuple[Tuple[int, ...], int]) -> Tuple[int, ...]:
    """Reconstruct visible vector from state (u, j)."""
    u, j = state
    return insert_zero(u, j)


def distance_upper_bound(m: int, r: int) -> int:
    """Return the conjectured target budget T = m(m+1)/2 + (r-1)(m-2)."""
    return m * (m + 1) // 2 + (r - 1) * (m - 2)
