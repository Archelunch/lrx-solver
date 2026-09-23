import unittest

try:
    import numpy as np

    from src.lrx.lifting_fast import INF, check_graph, lift_values, witness
except ImportError:  # numpy is optional for the rest of the lab
    np = None

from src.lrx.certificates import CertificateValidator
from src.lrx.evaluate import evaluate_projection
from src.lrx.exact_dp import ExactHqDp
from src.lrx.state import insert_zero
from src.lrx.table_bfs import Ranker, build_table


@unittest.skipIf(np is None, "numpy not installed")
class LiftingFastTests(unittest.TestCase):
    def reference_A(self, m, r, q):
        """A_q(v) from the independently tested pure-Python H DP."""
        dp = ExactHqDp(m, r, max_memo=2_000_000)
        values = {}
        for u in dp.states:
            for j in range(m + r):
                v = insert_zero(u, j)
                cost = dp.compute_H_q(q, u, j)
                values[v] = min(values.get(v, float("inf")), cost)
        return values

    def test_matches_pure_python_dp_on_every_state(self):
        for m, r in [(2, 2), (3, 2), (2, 3), (4, 2), (3, 3), (5, 2)]:
            p = build_table(m, r - 1)[1]["radius"]
            for q in {p, max(0, p - 2), p + 1}:
                a, *_ = lift_values(m, r, q)
                ref = self.reference_A(m, r, q)
                ranker = Ranker(m, r)
                for v, cost in ref.items():
                    got = int(a[ranker.rank(ranker.positions(v))])
                    want = int(INF) if cost == float("inf") else cost
                    self.assertEqual(got, want, (m, r, q, v))

    def test_report_matches_evaluate_projection(self):
        for m, r in [(4, 2), (5, 2), (3, 3), (4, 3)]:
            fast = check_graph(m, r)
            slow = evaluate_projection(m, r, max_cells=3_000_000)
            self.assertEqual(slow["status"], "COMPLETE")
            for key_fast, key_slow in [
                ("no_admissible_lift", "no_admissible_lift"),
                ("finite_over_budget", "finite_over_budget"),
                ("max_finite_A", "max_finite_length"),
                (
                    "lifting_bound_holds_on_this_graph",
                    "lifting_bound_holds_on_this_graph",
                ),
            ]:
                self.assertEqual(fast[key_fast], slow[key_slow], (m, r, key_fast))
            self.assertEqual(fast["A_below_distance_violations"], 0)

    def test_witness_words_replay(self):
        m, r = 5, 2
        rep = check_graph(m, r, keep_layers=True)
        layers, trans, h = rep["_layers"], rep["_trans"], rep["_h"]
        q = rep["projection_cap_q"]
        space = trans[0]
        finite = np.nonzero(h < INF)[0]
        for code in finite[:: max(1, len(finite) // 40)]:
            word = witness(m, r, q, layers, trans, code)
            pos = space.unrank(np.array([code]))[0]
            v = [0] * (m + r)
            for t, p in enumerate(pos[:m], 1):
                v[p] = t
            j = int(pos[m])
            u = tuple(v[:j] + v[j + 1 :])
            cert = CertificateValidator(m, r).replay_word(word, (u, j))
            self.assertTrue(cert.terminal)
            self.assertLessEqual(cert.projection_length, q)
            self.assertEqual(len(word), int(h[code]))


if __name__ == "__main__":
    unittest.main()
