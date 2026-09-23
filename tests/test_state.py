"""Tests for state operations."""

import unittest
from src.lrx.state import (
    canonical_root,
    smaller_root,
    insert_zero,
    remove_zero_at,
    apply_L,
    apply_R,
    apply_X,
    apply_marked_L,
    apply_marked_R,
    apply_marked_X,
    is_terminal,
)


class TestStateOperations(unittest.TestCase):
    """Test basic state operations."""

    def test_canonical_root(self):
        """Test canonical root generation."""
        root = canonical_root(3, 2)
        self.assertEqual(root, (1, 2, 3, 0, 0))

    def test_smaller_root(self):
        """Test smaller root generation."""
        root = smaller_root(3, 2)
        self.assertEqual(root, (1, 2, 3, 0))

    def test_insert_remove_zero(self):
        """Test zero insertion and removal."""
        v = (1, 2, 3)
        # Insert at position 1
        v_zero = insert_zero(v, 1)
        self.assertEqual(v_zero, (1, 0, 2, 3))
        # Remove from position 1
        v_removed = remove_zero_at(v_zero, 1)
        self.assertEqual(v_removed, v)

    def test_cyclic_rotations(self):
        """Test L and R rotations."""
        v = (1, 2, 3, 4)
        # L: move first to end
        self.assertEqual(apply_L(v), (2, 3, 4, 1))
        # R: move last to start
        self.assertEqual(apply_R(v), (4, 1, 2, 3))
        # L then R should return to original
        self.assertEqual(apply_R(apply_L(v)), v)

    def test_swap_X(self):
        """Test swap operation X."""
        v = (1, 2, 3, 4)
        # Swap first two
        self.assertEqual(apply_X(v), (2, 1, 3, 4))
        # Apply twice -> identity
        self.assertEqual(apply_X(apply_X(v)), v)
        # Empty and single element
        self.assertEqual(apply_X(()), ())
        self.assertEqual(apply_X((1,)), (1,))

    def test_marked_L(self):
        """Test marked-zero L transitions."""
        u = (1, 2, 3)
        # j=0: stay in u, j -> n-1
        state, n = (u, 0), len(u) + 1
        next_state = apply_marked_L(state)
        self.assertEqual(next_state, (u, n - 1))

        # j>0: apply L to u, j -> j-1
        state = (u, 2)
        next_state = apply_marked_L(state)
        self.assertEqual(next_state, (apply_L(u), 1))

    def test_marked_R(self):
        """Test marked-zero R transitions."""
        u = (1, 2, 3)
        n = len(u) + 1

        # j=n-1: stay in u, j -> 0
        state = (u, n - 1)
        next_state = apply_marked_R(state)
        self.assertEqual(next_state, (u, 0))

        # j<n-1: apply R to u, j -> j+1
        state = (u, 1)
        next_state = apply_marked_R(state)
        self.assertEqual(next_state, (apply_R(u), 2))

    def test_marked_X(self):
        """Test marked-zero X transitions."""
        u = (1, 2, 3)

        # j in {0, 1}: swap j
        state = (u, 0)
        self.assertEqual(apply_marked_X(state), (u, 1))
        state = (u, 1)
        self.assertEqual(apply_marked_X(state), (u, 0))

        # j >= 2: apply X to u
        state = (u, 2)
        next_state = apply_marked_X(state)
        self.assertEqual(next_state, (apply_X(u), 2))

    def test_is_terminal(self):
        """Test terminal state detection."""
        m, r = 3, 2
        root = smaller_root(m, r)

        # Terminal: root and j >= m
        self.assertTrue(is_terminal((root, m), m, r))
        self.assertTrue(is_terminal((root, m + 1), m, r))

        # Not terminal: wrong u
        other_u = (1, 2, 0, 0)
        self.assertFalse(is_terminal((other_u, m), m, r))

        # Not terminal: j < m
        self.assertFalse(is_terminal((root, m - 1), m, r))


class TestMarkedStateConsistency(unittest.TestCase):
    """Test consistency of marked-zero operations."""

    def test_round_trip_with_vector(self):
        """Test conversion between vector and state."""
        from src.lrx.state import state_from_vector, vector_from_state

        v = (1, 2, 3, 0, 4)
        j = 3  # zero at position 3

        # v -> state -> v
        state = state_from_vector(v, j)
        v_recovered = vector_from_state(state)
        self.assertEqual(v_recovered, v)

    def test_root_operations_preserve_structure(self):
        """Test that operations preserve vector structure."""
        m, r = 2, 1
        root = canonical_root(m, r)

        # Apply and undo rotations
        v1 = apply_L(apply_R(root))
        self.assertEqual(v1, root)

        # Swap is self-inverse
        v2 = apply_X(apply_X(root))
        self.assertEqual(v2, root)


if __name__ == "__main__":
    unittest.main()
