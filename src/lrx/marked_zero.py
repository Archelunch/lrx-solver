"""Compatibility imports for the single trusted projection DP implementation."""

from .exact_dp import (
    ExactFeDp as ExcessBudgetDP,
    ExactHqDp,
    ResourceLimit,
    compute_marked_transitions as marked_transitions,
    three_vertex_distance,
)

__all__ = [
    "ExcessBudgetDP",
    "ExactHqDp",
    "ResourceLimit",
    "marked_transitions",
    "three_vertex_distance",
]
