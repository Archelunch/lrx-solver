"""Tests for BFS computation."""

import unittest

from src.lrx.reference_bfs import bfs_marked_zero
from src.lrx.state import smaller_root


class TestBFS(unittest.TestCase):
    """Test BFS distance computation."""

    def test_bfs_small_complete(self):
        """Test BFS on small complete problem."""
        m, r = 2, 1
        result = bfs_marked_zero(m, r, max_vertices=100000)

        self.assertEqual(result.status, "COMPLETE")
        self.assertGreater(result.vertices_explored, 0)

        # Smaller root at terminal position should be distance 0
        root_state = (smaller_root(m, r), m)
        dist = result.distance(root_state)
        self.assertEqual(dist, 0)

    def test_bfs_parent_pointers(self):
        """Test that parent pointers form a valid BFS tree."""
        m, r = 2, 1
        result = bfs_marked_zero(m, r, max_vertices=100000)

        # Verify parent pointers
        for state, distance in result.distances.items():
            if distance == 0:
                # Root has no parent
                self.assertNotIn(state, result.parent)
            else:
                # Non-root states should have parent with distance-1
                self.assertIn(state, result.parent)
                parent_state, _ = result.parent[state]
                self.assertEqual(result.distances[parent_state], distance - 1)

    def test_bfs_resource_limits(self):
        """Test that BFS respects resource limits."""
        m, r = 5, 3  # Larger instance

        # With very tight limit
        result = bfs_marked_zero(m, r, max_vertices=100, max_queue_size=50)

        # Should hit limit
        self.assertNotEqual(result.status, "COMPLETE")
        self.assertLessEqual(result.vertices_explored, 100)

    def test_bfs_path_reconstruction(self):
        """Test path reconstruction from parent pointers."""
        m, r = 2, 1
        result = bfs_marked_zero(m, r, max_vertices=100000)

        # Get a non-root state
        non_root_states = [s for s, d in result.distances.items() if d > 0]
        if non_root_states:
            state = non_root_states[0]
            path = result.path(state)

            # Path should be non-empty and contain only L, R, X
            self.assertIsNotNone(path)
            self.assertGreater(len(path), 0)
            for c in path:
                self.assertIn(c, "LRX")


class TestBFSOnSmallInstances(unittest.TestCase):
    """Test BFS on specific small instances."""

    def test_bfs_n4_m2_r2(self):
        """Test on n=4 (m=2, r=2)."""
        result = bfs_marked_zero(2, 2, max_vertices=10000)
        self.assertEqual(result.status, "COMPLETE")

    def test_bfs_n5_m3_r2(self):
        """Test on n=5 (m=3, r=2)."""
        result = bfs_marked_zero(3, 2, max_vertices=50000)
        self.assertEqual(result.status, "COMPLETE")

    def test_bfs_no_duplicate_distances(self):
        """Verify BFS correctly computes shortest distances."""
        m, r = 2, 2
        result = bfs_marked_zero(m, r, max_vertices=100000)

        # All distances should be unique (no two states at same distance have different true distances)
        # This is guaranteed by BFS property
        for state, distance in result.distances.items():
            if state in result.parent:
                parent_state, _ = result.parent[state]
                parent_dist = result.distances[parent_state]
                self.assertEqual(parent_dist + 1, distance)


class TestBFSResourceTracking(unittest.TestCase):
    """Test resource tracking in BFS."""

    def test_max_queue_tracking(self):
        """Test that max queue size is correctly tracked."""
        m, r = 3, 2
        result = bfs_marked_zero(m, r, max_vertices=100000)

        # Max queue should be positive and <= vertices explored
        self.assertGreater(result.max_queue_size, 0)
        self.assertLessEqual(result.max_queue_size, result.vertices_explored)

    def test_verbose_output(self):
        """Test verbose mode doesn't crash."""
        import sys
        from io import StringIO

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            # Use larger instance to guarantee progress output
            result = bfs_marked_zero(4, 2, max_vertices=100000, verbose=True)
            # Should have at least completed without error; progress may not print if < 10k vertices
            self.assertEqual(result.status, "COMPLETE")
            self.assertEqual(len(result.distances), 720)
        finally:
            sys.stderr = old_stderr


if __name__ == "__main__":
    unittest.main()
