"""Differential tests against literal marked-vector budget BFS."""

import unittest
from collections import deque
from math import inf

from src.lrx.exact_dp import ExactFeDp, ExactHqDp, ResourceLimit
from src.lrx.reference_bfs import bfs_visible
from src.lrx.certificates import (
    CertificateValidator,
    verify_family,
    verify_family_distance,
)
from src.lrx.state import canonical_root, state_counts


def literal_oracle(m, r, max_projection):
    root = canonical_root(m, r)
    distances, queue = {}, deque()
    for j in range(m, m + r):
        marked = root[:j] + (-1,) + root[j + 1 :]
        distances[marked, 0] = 0
        queue.append((marked, 0))
    while queue:
        v, used = queue.popleft()
        deleted = tuple(x for x in v if x != -1)
        swapped = list(v)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        for w in (v[1:] + v[:1], v[-1:] + v[:-1], tuple(swapped)):
            count = used + (tuple(x for x in w if x != -1) != deleted)
            key = w, count
            if count <= max_projection and key not in distances:
                distances[key] = distances[v, used] + 1
                queue.append(key)
    return distances


class ExactTests(unittest.TestCase):
    def test_exhaustive_literal_oracle_and_both_recurrences(self):
        for n in range(4, 8):
            for m in range(2, n - 1):
                r = n - m
                smaller = bfs_visible(m, r - 1)
                self.assertEqual(smaller.status, "COMPLETE")
                self.assertEqual(len(smaller.distances), state_counts(m, r)["smaller"])
                limit = max(smaller.distances.values()) + 4
                oracle = literal_oracle(m, r, limit)
                h, f = ExactHqDp(m, r), ExactFeDp(m, r, smaller.distances)
                for u, d in smaller.distances.items():
                    for j in range(n):
                        marked = u[:j] + (-1,) + u[j:]
                        best = inf
                        for q in range(limit + 1):
                            best = min(best, oracle.get((marked, q), inf))
                            actual = h.compute_H_q(q, u, j)
                            self.assertEqual(actual, best, (m, r, u, j, q))
                            if d <= q <= d + 4:
                                self.assertEqual(
                                    f.compute_F_e(q - d, u, j), best, (m, r, u, j, q)
                                )
                # Replay certificates from every marked state at full tested budget.
                for u in smaller.distances:
                    for j in range(n):
                        word = h.witness(limit, u, j)
                        if word is not None:
                            cert = CertificateValidator(m, r).replay_word(word, (u, j))
                            self.assertTrue(cert.terminal)
                            self.assertLessEqual(cert.projection_length, limit)
                            self.assertEqual(len(word), h.compute_H_q(limit, u, j))

    def test_incomplete_or_wrong_oracle_is_rejected(self):
        with self.assertRaises(ValueError):
            ExactFeDp(2, 2, {(1, 2, 0): 0})
        distances = bfs_visible(2, 1).distances
        distances[(2, 1, 0)] = 100
        with self.assertRaises(ValueError):
            ExactFeDp(2, 2, distances)

    def test_resource_limits_never_mean_infinity(self):
        with self.assertRaises(ResourceLimit):
            ExactHqDp(8, 2)
        h = ExactHqDp(2, 2, max_memo=24)
        with self.assertRaises(ResourceLimit):
            h.compute_H_q(1, (1, 2, 0), 2)
        self.assertTrue(h.incomplete)

    def test_isolated_mark_and_zero_budget_closure(self):
        h = ExactHqDp(2, 2)
        self.assertEqual(h.compute_H_q(0, (1, 2, 0), 0), 1)
        self.assertEqual(h.compute_H_q(0, (2, 1, 0), 2), inf)
        self.assertEqual(h.compute_H_q(1, (2, 1, 0), 2), 1)

    def test_family_both_markings(self):
        for k in range(2, 31):
            result = verify_family(k)
            self.assertTrue(result["verified_upper_bound"], k)
            self.assertEqual(len(result["marks"]), 2)
            self.assertFalse(result["lower_bound_checked"])

    def test_finite_family_exact_distance_ball_certificates(self):
        for k in range(2, 5):
            report = verify_family_distance(k)
            self.assertEqual(report["status"], "COMPLETE")
            self.assertTrue(report["lower_bound_checked"])
            self.assertEqual(report["exact_distance"], 6 * k - 2)
            self.assertEqual(sum(report["ball_radii"]), 6 * k - 3)
        report = verify_family_distance(2, max_vertices=1)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertIsNone(report["exact_distance"])
        self.assertFalse(report["lower_bound_checked"])

    def test_visible_count_and_known_small_radius(self):
        result = bfs_visible(2, 2)
        self.assertEqual(len(result.distances), 12)
        self.assertEqual(result.status, "COMPLETE")
        result = bfs_visible(3, 2, max_vertices=5)
        self.assertEqual(result.status, "INCOMPLETE")
        self.assertLessEqual(len(result.distances), 5)

    def test_input_rejection(self):
        h = ExactHqDp(2, 2)
        for q, u, j in [
            (-1, (1, 2, 0), 1),
            (1, (1, 1, 0), 2),
            (1, (1, 2, 0), -1),
            (True, (1, 2, 0), 2),
        ]:
            with self.assertRaises(ValueError):
                h.compute_H_q(q, u, j)
