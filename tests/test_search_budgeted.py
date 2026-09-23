"""Cache isolation and proof-facing selection checks; no live network."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from integrations.eval_cache import evaluate_cached
from src.lrx.candidates import Candidate
from src.lrx.evolve import Campaign


SPEC = {"kind": "bound", "expr": "T"}


def record(value=75, score=-100, failures=0, incomplete=0):
    return {"score": score, "eval": {"stopped": None, "graphs": [
        {"graph": "m8r3", "m": 8, "T": 48, "value_max": value,
         "feedback": True, "failures": failures, "incomplete": incomplete}]}}


class CacheTests(unittest.TestCase):
    def test_reuse_invalidation_corruption_and_heldout_isolation(self):
        result = {"valid": True, "candidate_hash": Candidate(SPEC).hash,
                  "graphs": [], "seconds": 1.2}
        with tempfile.TemporaryDirectory() as directory, \
                patch("integrations.eval_cache.evaluator.evaluate", return_value=result) as evaluate, \
                patch("integrations.eval_cache.evaluator.evaluator_hash", return_value="v1") as version:
            self.assertFalse(evaluate_cached(SPEC, cache_dir=directory)["cache_hit"])
            self.assertTrue(evaluate_cached(dict(SPEC, name="renamed"), cache_dir=directory)["cache_hit"])
            self.assertEqual(evaluate.call_count, 1)
            evaluate_cached(SPEC, "heldout", directory)
            self.assertEqual(evaluate.call_count, 2)
            version.return_value = "v2"
            self.assertFalse(evaluate_cached(SPEC, cache_dir=directory)["cache_hit"])
            for path in Path(directory).glob("*.json"):
                path.write_text("broken")
            self.assertFalse(evaluate_cached(SPEC, cache_dir=directory)["cache_hit"])

    def test_incomplete_is_never_cached(self):
        result = {"valid": True, "candidate_hash": Candidate(SPEC).hash,
                  "graphs": [{"incomplete": 1}], "seconds": 20}
        with tempfile.TemporaryDirectory() as directory, \
                patch("integrations.eval_cache.evaluator.evaluate", return_value=result) as evaluate:
            evaluate_cached(SPEC, cache_dir=directory)
            evaluate_cached(SPEC, cache_dir=directory)
            self.assertEqual(evaluate.call_count, 2)
            self.assertEqual(list(Path(directory).glob("*.json")), [])


class ObjectiveTests(unittest.TestCase):
    def campaign(self):
        c = object.__new__(Campaign)
        c.cfg = {"select": "ratio", "window": 2, "max_proposals": 8}
        return c

    def test_worst_ratio_precedes_mean_and_failures_precede_ratio(self):
        c = self.campaign()
        self.assertGreater(c.rank(record(74, -500)), c.rank(record(75, -1)))
        self.assertGreater(c.rank(record(75)), c.rank(record(48, failures=1)))
        self.assertGreater(c.rank(record(75)), c.rank(record(48, incomplete=1)))
        a = record()
        b = copy.deepcopy(a)
        b["eval"]["graphs"].append({"feedback": False, "m": 8, "T": 48,
                                     "value_max": 999, "failures": 500})
        self.assertEqual(c.rank(a), c.rank(b))

    def test_evox_reflects_when_only_mean_score_improved(self):
        c = self.campaign()
        c.best = lambda: record(75, -1)
        c.window_start = -75 / 48
        c.window_count = 0
        c.proposals = 2
        c.strategy = {"parent": "best"}
        c.strategy_history = []
        c.log = Mock()
        c.start_reflection = Mock()
        c.evox_window(2)
        self.assertEqual(c.strategy_history[0]["delta"], 0)
        c.start_reflection.assert_called_once_with("strategy")

    def test_zero_heldout_really_disables_evaluation(self):
        c = self.campaign()
        c.cfg["final_heldout_top"] = 0
        pool = Mock()
        c.final_heldout(pool)
        pool.submit.assert_not_called()
        self.assertEqual(c.heldout, [])
