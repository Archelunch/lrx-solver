"""Word certificates: replay and independent verification of candidate solutions.

Words are sequences of {L, R, X} letters. Trusted interpreter replays against
marked-zero state transitions, evaluates projection length, verifies termination,
and computes budget excess.

Certificate: includes word, claimed distance, parameters, and verification results.
"""

import json
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

from .state import (
    apply_marked_L,
    apply_marked_R,
    apply_marked_X,
    smaller_root,
    vector_from_state,
    canonical_root,
    validate_vector,
    state_from_vector,
)


@dataclass
class CertificateResult:
    """Result of replaying and verifying a certificate word."""

    m: int
    r: int
    word: str
    claimed_distance: Optional[int]
    word_length: int

    # Replay results
    replay_valid: bool
    replay_error: Optional[str]
    final_state: Optional[Tuple[Tuple[int, ...], int]]
    final_vector: Optional[Tuple[int, ...]]

    # Projection metrics
    projection_length: Optional[int]
    projection_sequence: Optional[str]

    # Budget metrics
    budget_excess: Optional[int]  # >= 0 if valid, None if invalid
    terminal: bool  # Does final state reach smaller root with j >= m?

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            "m": self.m,
            "r": self.r,
            "word": self.word,
            "claimed_distance": self.claimed_distance,
            "word_length": self.word_length,
            "replay_valid": self.replay_valid,
            "replay_error": self.replay_error,
            "projection_length": self.projection_length,
            "budget_excess": self.budget_excess,
            "terminal": self.terminal,
        }

    def json_str(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())


class CertificateValidator:
    """Replay and verify word certificates in marked-zero system."""

    def __init__(self, m: int, r: int):
        self.m = m
        self.r = r
        self.smaller_root = smaller_root(m, r)
        self.n = m + r

    def replay_word(
        self,
        word: str,
        start_state: Optional[Tuple[Tuple[int, ...], int]] = None,
        target_vector: Optional[Tuple[int, ...]] = None,
        max_steps: int = 100_000,
        budget: Optional[int] = None,
    ) -> CertificateResult:
        """Replay a word and return detailed verification result.

        Args:
            word: sequence of L, R, X letters (case-sensitive)
            start_state: initial marked-zero state; defaults to smaller root at position m
            target_vector: if provided, extract marked-zero pair from visible vector at first zero

        Returns:
            CertificateResult with full replay trace
        """
        if not isinstance(word, str) or len(word) > max_steps:
            raise ValueError("Word must be a string within max_steps")
        if budget is not None and (type(budget) is not int or budget < 0):
            raise ValueError("Budget must be a nonnegative integer")
        if target_vector is not None and start_state is not None:
            raise ValueError("Supply either start_state or target_vector, not both")
        # target_vector is a legacy name for the visible starting vector.
        if target_vector is not None:
            validate_vector(target_vector, self.m, self.r)
            # Find first zero in target vector
            zero_idx = None
            for idx, val in enumerate(target_vector):
                if val == 0:
                    zero_idx = idx
                    break
            if zero_idx is None:
                return CertificateResult(
                    m=self.m,
                    r=self.r,
                    word=word,
                    claimed_distance=None,
                    word_length=len(word),
                    replay_valid=False,
                    replay_error="Target vector has no zeros",
                    final_state=None,
                    final_vector=None,
                    projection_length=None,
                    projection_sequence=None,
                    budget_excess=None,
                    terminal=False,
                )
            # Remove marked zero to get u
            u = target_vector[:zero_idx] + target_vector[zero_idx + 1 :]
            start_state = (u, zero_idx)
        elif start_state is None:
            start_state = (self.smaller_root, self.m)
        initial_visible = vector_from_state(start_state)
        validate_vector(initial_visible, self.m, self.r)

        # Validate word format
        valid_letters = set("LRX")
        for i, letter in enumerate(word):
            if letter not in valid_letters:
                return CertificateResult(
                    m=self.m,
                    r=self.r,
                    word=word,
                    claimed_distance=None,
                    word_length=len(word),
                    replay_valid=False,
                    replay_error=f"Invalid letter '{letter}' at position {i}",
                    final_state=None,
                    final_vector=None,
                    projection_length=None,
                    projection_sequence=None,
                    budget_excess=None,
                    terminal=False,
                )

        # Replay
        current_state = start_state
        projection_ops = []

        try:
            for i, letter in enumerate(word):
                prev_state = current_state

                if letter == "L":
                    current_state = apply_marked_L(current_state)
                elif letter == "R":
                    current_state = apply_marked_R(current_state)
                elif letter == "X":
                    current_state = apply_marked_X(current_state)

                # Track projection: transitions that change u
                u_changed = prev_state[0] != current_state[0]
                if u_changed:
                    projection_ops.append(letter)
        except Exception as e:
            return CertificateResult(
                m=self.m,
                r=self.r,
                word=word,
                claimed_distance=None,
                word_length=len(word),
                replay_valid=False,
                replay_error=f"Execution error at position {i}: {str(e)}",
                final_state=None,
                final_vector=None,
                projection_length=None,
                projection_sequence=None,
                budget_excess=None,
                terminal=False,
            )

        # Check termination
        final_u, final_j = current_state
        is_terminal = final_u == self.smaller_root and self.m <= final_j < self.n

        # Reconstruct final visible vector
        final_vector = vector_from_state(current_state)
        literal_final = replay_visible(initial_visible, word, max_steps)
        if literal_final != final_vector:
            raise AssertionError("Marked and independent visible interpreters disagree")

        # Metrics
        projection_length = len(projection_ops)
        projection_sequence = "".join(projection_ops)

        budget_excess = (
            len(word) - budget if is_terminal and budget is not None else None
        )

        return CertificateResult(
            m=self.m,
            r=self.r,
            word=word,
            claimed_distance=None,
            word_length=len(word),
            replay_valid=True,
            replay_error=None,
            final_state=current_state,
            final_vector=final_vector,
            projection_length=projection_length,
            projection_sequence=projection_sequence,
            budget_excess=budget_excess if is_terminal else None,
            terminal=is_terminal,
        )

    def verify_candidate_vector(
        self, word: str, target_vector: Tuple[int, ...]
    ) -> Tuple[bool, str]:
        """Verify that word sorts a marked-zero state to the target vector's visible form.

        Returns: (success, message)
        """
        result = self.replay_word(word)

        if not result.replay_valid:
            return False, f"Replay failed: {result.replay_error}"

        if result.final_vector != target_vector:
            return (
                False,
                f"Final vector mismatch: got {result.final_vector}, expected {target_vector}",
            )

        return True, "Verified"


def canonical_word_family_k(k: int) -> str:
    """Return the explicit word W_k from Theorem 2.

    W_k = L^(k-1) X (RX)^(k-1) R^k X (LX)^(k-2) L^3
    """
    if k < 2:
        raise ValueError("k must be >= 2")

    word = "L" * (k - 1)  # L^(k-1)
    word += "X"  # X
    word += ("RX") * (k - 1)  # (RX)^(k-1)
    word += "R" * k  # R^k
    word += "X"  # X
    word += ("LX") * (k - 2)  # (LX)^(k-2)
    word += "L" * 3  # L^3

    return word


def family_parameters(k: int) -> Tuple[int, int, int]:
    """Return (m, r, n) for the regression family at given k.

    m = 8k - 1, r = 2, n = m + r = 8k + 1
    """
    if type(k) is not int or not 2 <= k <= 1000:
        raise ValueError("Require integer 2 <= k <= 1000")
    m = 8 * k - 1
    r = 2
    n = m + r
    return m, r, n


def family_vector(k: int) -> Tuple[int, ...]:
    """Return the vector v_{m,k} = (1,...,k, 0, k+1,...,m-k+1, 0, m-k+2,...,m).

    From Theorem 2, equation (8).
    """
    m, _, _ = family_parameters(k)
    v = list(range(1, k + 1))  # (1, ..., k)
    v.append(0)  # first zero
    v.extend(range(k + 1, m - k + 2))  # (k+1, ..., m-k+1)
    v.append(0)  # second zero
    v.extend(range(m - k + 2, m + 1))  # (m-k+2, ..., m)
    return tuple(v)


def replay_visible(v, word, max_steps=100_000):
    """Independent literal-list interpreter for upper-bound certificates."""
    if not isinstance(word, str) or len(word) > max_steps:
        raise ValueError("Invalid or oversized word")
    values = list(v)
    for op in word:
        if op == "L":
            values.append(values.pop(0))
        elif op == "R":
            values.insert(0, values.pop())
        elif op == "X":
            values[0], values[1] = values[1], values[0]
        else:
            raise ValueError("Illegal operation")
    return tuple(values)


def verify_family(k):
    """Check both marked projections and the explicit sorting word; no lower bound."""
    m, r, _ = family_parameters(k)
    v, word = family_vector(k), canonical_word_family_k(k)
    checks = []
    for j, value in enumerate(v):
        if value == 0:
            result = CertificateValidator(m, r).replay_word(
                word, state_from_vector(v, j)
            )
            checks.append(
                {
                    "mark": j,
                    "terminal": result.terminal,
                    "projection": result.projection_length,
                }
            )
    valid = (
        len(word) == 6 * k - 2
        and replay_visible(v, word) == canonical_root(m, r)
        and all(c["terminal"] and c["projection"] == 5 * k - 3 for c in checks)
    )
    return {
        "k": k,
        "verified_upper_bound": valid,
        "word_length": len(word),
        "word": word,
        "marks": checks,
        "lower_bound_checked": False,
    }


def verify_family_distance(k, max_vertices=50_000):
    """Finite exact-distance certificate from disjoint complete balls."""
    if type(max_vertices) is not int or not 1 <= max_vertices <= 1_000_000:
        raise ValueError("Invalid ball vertex limit")
    report = verify_family(k)
    if not report["verified_upper_bound"]:
        raise AssertionError("Family upper bound failed")
    distance = report["word_length"]
    left_radius = distance // 2 - 1
    right_radius = distance - 1 - left_radius

    def ball(start, radius):
        seen, queue = {start}, deque([(start, 0)])
        while queue:
            v, depth = queue.popleft()
            if depth == radius:
                continue
            for op in "LRX":
                target = replay_visible(v, op)
                if target not in seen:
                    if len(seen) >= max_vertices:
                        return None
                    seen.add(target)
                    queue.append((target, depth + 1))
        return seen

    m, r, _ = family_parameters(k)
    left = ball(family_vector(k), left_radius)
    right = ball(canonical_root(m, r), right_radius) if left is not None else None
    report["ball_radii"] = [left_radius, right_radius]
    if left is None or right is None:
        report.update(status="INCOMPLETE", exact_distance=None)
    else:
        report.update(
            status="COMPLETE",
            ball_sizes=[len(left), len(right)],
            lower_bound_checked=True,
            exact_distance=distance if left.isdisjoint(right) else None,
        )
    return report
