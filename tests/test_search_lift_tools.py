"""Route B analysis tools in autoresearch/ agree with the trusted lifting engine."""

import importlib.util
import unittest
from pathlib import Path

import numpy as np

from src.lrx.lifting_fast import (
    INF,
    build_transitions,
    check_graph,
    h_layers,
    lift_values,
)
from src.lrx.table_bfs import Ranker

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "autoresearch" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sweep_tool = _load("lift_sweep")
forward_tool = _load("lift_forward")
targeted_tool = _load("lift_targeted")

GRAPHS = [(3, 2), (3, 3), (4, 2), (4, 3)]


class LiftSweepTest(unittest.TestCase):
    def test_every_layer_equals_h_layers(self):
        for m, r in GRAPHS:
            trans = build_transitions(m, r)
            for q, h in sweep_tool.layer_iter(trans, m, r, 12):
                expected = h_layers(m, r, q, transitions=trans)[0]
                self.assertTrue(np.array_equal(h, expected), (m, r, q))

    def test_reshape_min_equals_minimum_at(self):
        for m, r in GRAPHS:
            a, h, _, _ = lift_values(m, r, 9)
            self.assertTrue(np.array_equal(sweep_tool.lift_min(h, r), a), (m, r))

    def test_row_at_P_matches_check_graph(self):
        for m, r in GRAPHS:
            ref = check_graph(m, r)
            p = ref["smaller_radius_P"]
            rep = sweep_tool.sweep(m, r, p, p)
            row = rep["rows"][0]
            self.assertEqual(rep["P"], p)
            self.assertEqual(row["no_admissible_lift"], ref["no_admissible_lift"])
            self.assertEqual(row["over_budget"], ref["finite_over_budget"])
            self.assertEqual(row["max_finite_A"], ref["max_finite_A"])
            self.assertEqual(row["hist_A_minus_budget"], ref["histogram_A_minus_cap"])
            self.assertEqual(row["A_eq_d"], ref["A_equals_distance"])
            self.assertEqual(row["A_below_d"], 0)

    def test_window_is_monotone_and_stops_when_exact(self):
        rep = sweep_tool.sweep(4, 3, 0, 40)
        maxima = [row["max_finite_A"] for row in rep["rows"] if row["max_finite_A"]]
        lifts = [row["no_admissible_lift"] for row in rep["rows"]]
        self.assertEqual(lifts, sorted(lifts, reverse=True))
        self.assertEqual(rep["rows"][-1]["A_eq_d"], rep["visible_states"])
        self.assertLess(rep["rows"][-1]["q"], 40)
        self.assertEqual(rep["q_all_equal_d"], rep["rows"][-1]["q"])
        self.assertTrue(maxima)

    def test_listed_vectors_carry_deletion_data(self):
        rep = sweep_tool.sweep(4, 3, 10, 10, vectors=[(2, 1, 0, 0, 0, 4, 3)])
        item = rep["rows"][0]["requested"][0]
        self.assertEqual(item["v"], [2, 1, 0, 0, 0, 4, 3])
        self.assertEqual([x["j"] for x in item["deletions"]], [2, 3, 4])
        self.assertEqual(item["A"], min(x["H"] for x in item["deletions"]))


class LiftForwardTest(unittest.TestCase):
    """The forward search shares no DP code with lifting_fast; values must agree."""

    def test_forward_equals_layer_dp_on_marked_states(self):
        for (m, r), stride in zip(GRAPHS, (1, 1, 1, 5)):
            dist, p, _ = forward_tool.smaller_table(m, r)
            ranker = Ranker(m, r)
            trans = build_transitions(m, r)
            for q in (max(0, p - 2), p, p + 1):
                h = h_layers(m, r, q, transitions=trans)[0]
                for code in range(0, ranker.size, stride):
                    v = ranker.vector(ranker.unrank(code))
                    zeros = [i for i, x in enumerate(v) if x == 0]
                    for index, j in enumerate(zeros):
                        u = v[:j] + v[j + 1 :]
                        res = forward_tool.forward_h(m, r, u, j, q, dist, witness=False)
                        got = int(INF) if res["H"] is None else res["H"]
                        self.assertEqual(got, int(h[r * code + index]), (m, r, q, v, j))

    def test_check_vector_replays_witnesses(self):
        dist, p, _ = forward_tool.smaller_table(4, 3)
        res = forward_tool.check_vector(4, 3, (2, 1, 0, 0, 0, 4, 3), p, dist, 10**6)
        self.assertEqual(res["status"], "COMPLETE")
        for row in res["deletions"]:
            if row["H"] is not None:
                self.assertEqual(len(row["word"]), row["H"])
                self.assertTrue(row["replay"]["terminal"])
                self.assertLessEqual(row["replay"]["projection"], p)
        self.assertEqual(res["A"], min(x["H"] for x in res["deletions"] if x["H"]))

    def test_state_cap_is_incomplete_not_infinite(self):
        dist, p, _ = forward_tool.smaller_table(4, 3)
        res = forward_tool.check_vector(4, 3, (2, 1, 0, 0, 0, 4, 3), p + 3, dist, 3)
        self.assertEqual(res["status"], "INCOMPLETE")
        self.assertIsNone(res["A"])


class LiftTargetedTest(unittest.TestCase):
    def test_full_coverage_reproduces_over_budget_list(self):
        for m, r in ((3, 3), (4, 3), (3, 4)):
            p = check_graph(m, r)["smaller_radius_P"]
            rep = targeted_tool.run(m, r, p, 10**6, 1, None)
            ranker = Ranker(m, r)
            self.assertEqual(rep["covered_vectors"], ranker.size)
            self.assertEqual(rep["incomplete_pairs"], [])
            a = lift_values(m, r, p)[0]
            expected = sorted(
                list(ranker.vector(ranker.unrank(code)))
                for code in range(ranker.size)
                if a[code] > p + m - 2
            )
            self.assertEqual(sorted(rep["over_budget_vectors"]), expected, (m, r))

    def test_capped_flagged_vectors_are_unresolved_not_cleared(self):
        p = check_graph(4, 3)["smaller_radius_P"]
        rep = targeted_tool.run(4, 3, p, 10**6, 1, None, flag_max_states=3)
        flagged = [x["v"] for x in rep["flagged_vectors"]]
        self.assertTrue(flagged)
        self.assertEqual(rep["unresolved_vectors"], flagged)
        self.assertEqual(rep["over_budget_vectors"], [])

    def test_far_layer_only_is_partial(self):
        rep = targeted_tool.run(4, 3, 0, 10**6, 1, None)
        self.assertEqual(sum(rep["far_layer_sizes"].values()) * 7, rep["pairs"])
        self.assertLess(rep["covered_vectors"], Ranker(4, 3).size)


if __name__ == "__main__":
    unittest.main()
