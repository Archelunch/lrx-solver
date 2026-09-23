import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.lrx import evaluator
from src.lrx.certificates import replay_visible
from src.lrx.evolve import run_campaign
from src.lrx.feedback import MAX_BYTES, compress, word_comparison
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]
SEED = str(ROOT / "candidates/baselines/rules_bubble.json")
SPEC = json.loads(Path(SEED).read_text())


class WordComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()
        cls.result = evaluator.evaluate(SPEC, split="heldout")

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_words_replay_and_optimal_is_shortest(self):
        words = word_comparison(self.result, SPEC, min_m=3)
        self.assertIsNotNone(words)
        graph = next(g for g in self.result["graphs"] if g["graph"] == words["graph"])
        self.assertTrue(graph["feedback"])
        m, r = graph["m"], graph["r"]
        root = tuple(range(1, m + 1)) + (0,) * r
        v = tuple(words["v"])
        self.assertEqual(len(words["optimal_word"]), words["d"])
        self.assertEqual(replay_visible(v, words["optimal_word"]), root)
        self.assertEqual(replay_visible(v, words["controller_word"]), root)
        self.assertEqual(words["controller_len"], len(words["controller_word"]))
        self.assertEqual(words["controller_len"], graph["largest"][0]["value"])
        # every uphill step must be repaid by a later downhill step
        self.assertEqual(
            words["controller_len"],
            words["d"]
            + 2 * words["controller_uphill_total"]
            + words["controller_flat_total"],
        )

    def test_heldout_graphs_never_used(self):
        held = {g["graph"] for g in self.result["graphs"] if not g["feedback"]}
        self.assertTrue(held)
        for min_m in (2, 3, 4, 5):
            words = word_comparison(self.result, SPEC, min_m=min_m)
            if words:
                self.assertNotIn(words["graph"], held)

    def test_compress_adds_words_only_with_spec_and_large_m(self):
        self.assertNotIn("word_vs_optimal", compress(self.result))
        self.assertNotIn("word_vs_optimal", compress(self.result, spec=SPEC))
        with patch("src.lrx.feedback.WORDS_MIN_M", 3):
            fb = compress(self.result, spec=SPEC)
        self.assertIn("word_vs_optimal", fb)
        self.assertLessEqual(len(json.dumps(fb)), MAX_BYTES)
        for name in ("m4r3", "m5r3"):
            self.assertNotIn(name, json.dumps(fb))

    def test_non_rules_or_invalid_gets_nothing(self):
        self.assertIsNone(word_comparison(self.result, {"kind": "bound", "expr": 1}, 3))
        self.assertIsNone(word_comparison({"valid": False}, SPEC, 3))


class FeedbackWordsCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_flag_controls_feedback(self):
        for flag in (False, True):
            cfg = {
                "name": f"fw-{flag}",
                "engine": "sequential",
                "kinds": ["rules"],
                "seeds": [SEED],
                "max_proposals": 3,
                "batch": 3,
                "eval_workers": 2,
                "seed": 2,
                "feedback_words": flag,
            }
            run_dir = self.data.base / f"fw-{flag}"
            with patch("src.lrx.feedback.WORDS_MIN_M", 3):
                run_campaign(cfg, run_dir)
            events = [
                json.loads(line)
                for line in (run_dir / "events.jsonl").read_text().splitlines()
            ]
            seed = next(
                e for e in events if e["event"] == "candidate" and e["mode"] == "seed"
            )
            self.assertEqual("word_vs_optimal" in seed["feedback"], flag)


if __name__ == "__main__":
    unittest.main()
