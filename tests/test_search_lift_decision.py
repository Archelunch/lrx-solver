"""Bounded decisions agree with independent exhaustive layer DP."""

import unittest

from src.lrx.lifting_fast import INF, lift_values
from src.lrx.table_bfs import Ranker
from tests.test_search_lift_tools import forward_tool


class LiftDecisionTests(unittest.TestCase):
    def test_all_small_visible_states_at_both_sides_of_bound(self):
        m, r = 3, 3
        dist, p, _ = forward_tool.smaller_table(m, r)
        ranker = Ranker(m, r)
        for q in (p - 1, p, p + 1):
            a = lift_values(m, r, q)[0]
            for code in range(ranker.size):
                v = ranker.vector(ranker.unrank(code))
                exact = int(a[code])
                bounds = (max(0, exact - 1), exact) if exact < int(INF) else (p, p + 2)
                for bound in bounds:
                    result = forward_tool.decide_vector(m, r, v, q, bound, dist)
                    self.assertEqual(result["status"], "COMPLETE")
                    self.assertEqual(result["within_bound"], exact < int(INF) and exact <= bound)

    def test_resource_exhaustion_is_not_a_negative_answer(self):
        dist, p, _ = forward_tool.smaller_table(3, 3)
        result = forward_tool.decide_vector(3, 3, (3, 2, 1, 0, 0, 0), p, 30, dist, max_states=0)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIsNone(result["within_bound"])

    def test_root_stops_after_one_zero_deletion(self):
        dist, p, _ = forward_tool.smaller_table(3, 3)
        result = forward_tool.decide_vector(3, 3, (1, 2, 3, 0, 0, 0), p, 0, dist)
        self.assertTrue(result["within_bound"])
        self.assertEqual(len(result["deletions"]), 1)
