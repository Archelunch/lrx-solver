"""A distance-pruned frontier must not be confused with infinite lift cost."""
import unittest
from tests.test_search_lift_tools import forward_tool


class LiftPruningTests(unittest.TestCase):
    def test_early_exhaustion_is_only_a_bounded_negative(self):
        dist, p, _ = forward_tool.smaller_table(3, 3)
        u = (3, 2, 1, 0, 0)
        bounded = forward_tool.forward_h(3, 3, u, 5, p + 10, dist, max_length=1)
        exact = forward_tool.forward_h(3, 3, u, 5, p + 10, dist)
        self.assertEqual(bounded['status'], 'COMPLETE_BOUND')
        self.assertEqual(bounded['lower_bound'], 2)
        self.assertIsNone(bounded['H'])
        self.assertEqual(exact['status'], 'COMPLETE')
        self.assertGreater(exact['H'], 1)
        self.assertLess(bounded['states'], exact['states'])
