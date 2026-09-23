import json
import unittest
from pathlib import Path

from src.lrx import evaluator
from src.lrx.feedback import MAX_BYTES, compress, estimate_tokens
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]
BINOM = ["floordiv", ["mul", "n", ["sub", "n", 1]], 2]


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_sound_bound_is_feasible(self):
        res = evaluator.evaluate({"kind": "bound", "expr": BINOM}, split="train")
        self.assertTrue(res["valid"])
        self.assertTrue(res["feasible"])
        self.assertEqual(
            {g["graph"] for g in res["graphs"]}, {"m3r2", "m2r3", "m4r2", "m3r3"}
        )
        self.assertTrue(all(g["failures"] == 0 for g in res["graphs"]))
        self.assertLess(res["score"], 0)  # slack is penalised

    def test_unsound_bound_stops_at_sanity(self):
        res = evaluator.evaluate({"kind": "bound", "expr": 3}, split="train")
        self.assertFalse(res["feasible"])
        self.assertEqual(res["stopped"], "sanity failure; later tiers skipped")
        self.assertTrue(all(g["role"] == "sanity" for g in res["graphs"]))
        self.assertLess(res["score"], -evaluator.FAIL_WEIGHT)
        worst = res["graphs"][0]["worst"][0]
        self.assertIn("< d=", worst["reason"])

    def test_sanity_is_exhaustive(self):
        res = evaluator.evaluate({"kind": "bound", "expr": BINOM}, split="sanity")
        self.assertEqual(res["graphs"][0]["checked"], 60)  # 5!/2!

    def test_heldout_is_not_feedback(self):
        res = evaluator.evaluate({"kind": "bound", "expr": BINOM}, split="heldout")
        held = [g for g in res["graphs"] if g["role"] == "heldout"]
        self.assertEqual(len(held), 2)
        self.assertTrue(all(g["feedback"] is False for g in held))
        self.assertEqual(set(res["heldout"]), {"m4r3", "m5r3"})
        self.assertNotIn("m4r3", res["instances"])
        fb = json.dumps(compress(res))
        self.assertNotIn("m4r3", fb)
        self.assertNotIn("m5r3", fb)

    def test_rules_words_replayed_and_scored(self):
        spec = json.loads((ROOT / "candidates/baselines/rules_bubble.json").read_text())
        res = evaluator.evaluate(spec, split="train")
        self.assertTrue(res["valid"])
        for g in res["graphs"]:
            self.assertEqual(g["failures"], 0)
            self.assertGreaterEqual(g["gap_mean"], 0)
            self.assertGreaterEqual(g["value_max"], g["radius"])

    def test_broken_rules_are_unsolved_not_counterexamples(self):
        res = evaluator.evaluate({"kind": "rules", "rules": [{"if": 1, "do": "X"}]})
        g = res["graphs"][0]
        self.assertGreater(g["failures"], 0)
        self.assertIn("UNSOLVED", g["failure_kinds"])

    def test_potential_local_check(self):
        res = evaluator.evaluate(
            {"kind": "potential", "expr": ["add", "disp_sum", "cinv"]}
        )
        g = res["graphs"][0]
        self.assertGreater(g["failures"], 0)
        reasons = [w["reason"] for w in g["worst"]]
        self.assertTrue(reasons)
        self.assertTrue(
            all(r.startswith(("no descent", "phi=")) for r in reasons), reasons
        )

    def test_radius_kind(self):
        res = evaluator.evaluate({"kind": "radius", "expr": BINOM})
        self.assertTrue(res["feasible"])
        res = evaluator.evaluate({"kind": "radius", "expr": 1})
        self.assertFalse(res["feasible"])

    def test_invalid_candidate(self):
        res = evaluator.evaluate({"kind": "bound", "expr": "unknown_var"})
        self.assertFalse(res["valid"])
        self.assertEqual(res["score"], -1e6)

    def test_graph_filter_keeps_sanity_gate(self):
        res = evaluator.evaluate({"kind": "bound", "expr": BINOM}, graphs={"m4r2"})
        self.assertEqual({g["graph"] for g in res["graphs"]}, {"m3r2", "m2r3", "m4r2"})

    def test_certify_whole_graph(self):
        ok = evaluator.certify({"kind": "bound", "expr": BINOM}, 4, 2)
        self.assertTrue(ok["holds_on_graph"])
        self.assertEqual(ok["states"], 360)
        bad = evaluator.certify({"kind": "bound", "expr": 5}, 4, 2)
        self.assertFalse(bad["holds_on_graph"])
        self.assertGreater(bad["failures"], 0)

    def test_lock_mismatch_refused(self):
        lock = json.loads(self.data.lock.read_text())
        saved = dict(lock)
        lock["m3_r2"] = "0" * 64
        self.data.lock.write_text(json.dumps(lock))
        evaluator._TABLES.clear()
        try:
            with self.assertRaises(ValueError):
                evaluator.get_table(3, 2)
        finally:
            self.data.lock.write_text(json.dumps(saved))
            evaluator._TABLES.clear()

    def test_feedback_is_compact(self):
        spec = {"kind": "potential", "expr": ["add", "disp_sum", "cinv"]}
        fb = compress(evaluator.evaluate(spec))
        self.assertLessEqual(len(json.dumps(fb)), MAX_BYTES)
        self.assertLessEqual(estimate_tokens(fb), 2000)
        self.assertIn("failures", fb)
        self.assertIn("features", fb["failures"][0])

    def test_deterministic(self):
        spec = {"kind": "bound", "expr": BINOM}
        a = evaluator.evaluate(spec)
        b = evaluator.evaluate(spec)
        a.pop("seconds"), b.pop("seconds")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
