"""Position rewrites preserve absent-label and token-binding semantics."""

import json
import unittest
from pathlib import Path

from integrations.simplify import simplify_positions
from src.lrx.candidates import Candidate, run_rules
from src.lrx.dsl import Env, compile_expr
from src.lrx.table_bfs import Ranker


class SimplifyTests(unittest.TestCase):
    def test_lookup_matches_sum_including_out_of_range_registers(self):
        before = ["sum_tokens", ["if", ["eq", "t", "r0"], "p", 0]]
        after = simplify_positions(before)
        left, right = compile_expr(before), compile_expr(after)
        ranker = Ranker(3, 2)
        for code in range(ranker.size):
            v = ranker.vector(ranker.unrank(code))
            for target in range(-2, 6):
                env = Env(v, 3, 2, extra={"r0": target})
                self.assertEqual(left(env), right(env))

    def test_token_dependent_target_is_not_rewritten(self):
        expr = ["sum_tokens", ["if", ["eq", "t", ["add", "t", 1]], "p", 0]]
        self.assertEqual(simplify_positions(expr), expr)

    def test_full_controller_words_identical_on_all_m4r2_states(self):
        root = Path(__file__).resolve().parents[1]
        spec = json.loads((root / "candidates/leads/49ab346cb44b2f1b.json").read_text())
        compact = simplify_positions(spec)
        self.assertNotEqual(spec, compact)
        a, b = Candidate(spec), Candidate(compact)
        ranker = Ranker(4, 2)
        for code in range(ranker.size):
            v = ranker.vector(ranker.unrank(code))
            self.assertEqual(run_rules(a, v, 4, 2, 144), run_rules(b, v, 4, 2, 144))
