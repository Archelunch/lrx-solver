"""Tests for bounded beam-search candidate runner.

Replaces the old broken random-root runner tests.
All tests are deterministic; no network calls; no exec/eval.
"""

import json
import os
import tempfile
import unittest

from src.lrx.candidate_runner import (
    WORK_CAPS,
    Candidate,
    CandidateEvaluator,
    EvaluationResult,
    OfflinePolicyProposer,
    _dataset_hash,
    _policy_hash,
    _state_from_visible,
    beam_search,
    parse_policy,
    run_experiment,
)
from src.lrx.provider_adapter import OfflineMockProposer, ProposalBudget
from src.lrx.state import canonical_root, is_terminal


# ---------------------------------------------------------------------------
# parse_policy
# ---------------------------------------------------------------------------


class TestParsePolicy(unittest.TestCase):
    def test_valid_dict(self):
        p = parse_policy({"weights": [3, 3, 2], "beam_width": 10, "max_steps": 200})
        self.assertEqual(p["weights"], [3, 3, 2])
        self.assertEqual(p["beam_width"], 10)
        self.assertEqual(p["max_steps"], 200)

    def test_valid_json_string(self):
        s = '{"weights": [1, 2, 3], "beam_width": 5, "max_steps": 100}'
        p = parse_policy(s)
        self.assertEqual(p["weights"], [1, 2, 3])

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy(
                {"weights": [1, 1, 1], "beam_width": 5, "max_steps": 100, "extra": 0}
            )

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1, 1, 1], "beam_width": 5})

    def test_invalid_json_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy("{bad json}")

    def test_all_zero_weights_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [0, 0, 0], "beam_width": 5, "max_steps": 100})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [-1, 1, 1], "beam_width": 5, "max_steps": 100})

    def test_weight_over_max_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1001, 1, 1], "beam_width": 5, "max_steps": 100})

    def test_beam_width_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1, 1, 1], "beam_width": 0, "max_steps": 100})

    def test_beam_width_over_cap_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy(
                {
                    "weights": [1, 1, 1],
                    "beam_width": WORK_CAPS["max_beam_width"] + 1,
                    "max_steps": 100,
                }
            )

    def test_max_steps_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1, 1, 1], "beam_width": 5, "max_steps": 0})

    def test_max_steps_over_cap_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy(
                {
                    "weights": [1, 1, 1],
                    "beam_width": 5,
                    "max_steps": WORK_CAPS["max_steps"] + 1,
                }
            )

    def test_wrong_weights_length_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1, 2], "beam_width": 5, "max_steps": 100})

    def test_non_int_weight_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy({"weights": [1.5, 1, 1], "beam_width": 5, "max_steps": 100})

    def test_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy(42)

    def test_returns_copy(self):
        orig = {"weights": [1, 1, 1], "beam_width": 5, "max_steps": 100}
        p = parse_policy(orig)
        p["beam_width"] = 99
        self.assertEqual(orig["beam_width"], 5)  # original unchanged


# ---------------------------------------------------------------------------
# _state_from_visible
# ---------------------------------------------------------------------------


class TestStateFromVisible(unittest.TestCase):
    def test_zero_at_end(self):
        v = (1, 2, 0)
        u, j = _state_from_visible(v, 2, 1)
        self.assertEqual(j, 2)
        self.assertEqual(u, (1, 2))

    def test_zero_at_front(self):
        v = (0, 1, 2)
        u, j = _state_from_visible(v, 2, 1)
        self.assertEqual(j, 0)
        self.assertEqual(u, (1, 2))

    def test_zero_in_middle(self):
        v = (1, 0, 2)
        u, j = _state_from_visible(v, 2, 1)
        self.assertEqual(j, 1)
        self.assertEqual(u, (1, 2))

    def test_no_zero_raises(self):
        with self.assertRaises(ValueError):
            _state_from_visible((1, 2, 3), 2, 1)


# ---------------------------------------------------------------------------
# Candidate dataclass
# ---------------------------------------------------------------------------


class TestCandidate(unittest.TestCase):
    def test_creation(self):
        c = Candidate(word="LRX", m=2, r=1, parent_policy="p", seed=42, cost=3)
        self.assertEqual(c.word, "LRX")
        self.assertEqual(c.cost, 3)

    def test_hash_deterministic(self):
        c1 = Candidate(word="LRLX", m=2, r=1, parent_policy="p", seed=42, cost=4)
        c2 = Candidate(word="LRLX", m=2, r=1, parent_policy="p", seed=42, cost=4)
        self.assertEqual(c1.hash(), c2.hash())

    def test_hash_differs_for_different_words(self):
        c1 = Candidate(word="LRX", m=2, r=1, parent_policy="p", seed=42, cost=3)
        c2 = Candidate(word="LRL", m=2, r=1, parent_policy="p", seed=42, cost=3)
        self.assertNotEqual(c1.hash(), c2.hash())

    def test_to_dict_keys(self):
        c = Candidate(word="L", m=2, r=1, parent_policy="test", seed=0, cost=1)
        d = c.to_dict()
        self.assertIn("word", d)
        self.assertIn("m", d)
        self.assertIn("seed", d)


# ---------------------------------------------------------------------------
# CandidateEvaluator
# ---------------------------------------------------------------------------


class TestCandidateEvaluator(unittest.TestCase):
    def test_valid_word(self):
        ev = CandidateEvaluator(m=2, r=1)
        c = Candidate(word="LRX", m=2, r=1, parent_policy="p", seed=0, cost=3)
        r = ev.evaluate(c)
        self.assertIsInstance(r, EvaluationResult)
        self.assertTrue(r.valid)

    def test_invalid_letter_rejected(self):
        ev = CandidateEvaluator(m=2, r=1)
        c = Candidate(word="LQX", m=2, r=1, parent_policy="p", seed=0, cost=3)
        r = ev.evaluate(c)
        self.assertFalse(r.valid)

    def test_terminal_flag_is_bool(self):
        ev = CandidateEvaluator(m=2, r=1)
        c = Candidate(word="L", m=2, r=1, parent_policy="p", seed=0, cost=1)
        r = ev.evaluate(c)
        self.assertIsInstance(r.terminal, bool)

    def test_to_dict_structure(self):
        ev = CandidateEvaluator(m=2, r=1)
        c = Candidate(word="X", m=2, r=1, parent_policy="p", seed=0, cost=1)
        r = ev.evaluate(c)
        d = r.to_dict()
        self.assertIn("candidate", d)
        self.assertIn("valid", d)
        self.assertIn("terminal", d)
        self.assertIn("timestamp", d)


# ---------------------------------------------------------------------------
# beam_search
# ---------------------------------------------------------------------------


class TestBeamSearch(unittest.TestCase):
    """Behavioural tests: beam_search must find correct words for known cases."""

    DEFAULT_POLICY = {"weights": [3, 3, 2], "beam_width": 15, "max_steps": 500}

    def _check_word_sorts(self, m, r, vis, word):
        """Verify word sorts vis to terminal via independent replay."""
        from src.lrx.certificates import CertificateValidator

        start_state = _state_from_visible(tuple(vis), m, r)
        cert = CertificateValidator(m, r).replay_word(word, start_state=start_state)
        self.assertTrue(cert.replay_valid, f"Replay failed: {cert.replay_error}")
        self.assertTrue(cert.terminal, f"Word '{word}' did not reach terminal")

    def test_already_sorted_returns_empty_word(self):
        m, r = 2, 1
        vis = canonical_root(m, r)  # (1, 2, 0)
        state = _state_from_visible(vis, m, r)
        self.assertTrue(is_terminal(state, m, r))
        word = beam_search(m, r, state, self.DEFAULT_POLICY)
        self.assertEqual(word, "")

    def test_sorts_simple_2_1(self):
        m, r = 2, 1
        # (2, 1, 0) — X swaps to (1, 2, 0)
        vis = (2, 1, 0)
        state = _state_from_visible(vis, m, r)
        word = beam_search(m, r, state, self.DEFAULT_POLICY)
        self.assertNotEqual(word, "UNSOLVED")
        self._check_word_sorts(m, r, vis, word)

    def test_sorts_zero_at_front_2_1(self):
        m, r = 2, 1
        # (0, 1, 2) — L moves marked zero to end
        vis = (0, 1, 2)
        state = _state_from_visible(vis, m, r)
        word = beam_search(m, r, state, self.DEFAULT_POLICY)
        self.assertNotEqual(word, "UNSOLVED")
        self._check_word_sorts(m, r, vis, word)

    def test_sorts_zero_in_middle_2_1(self):
        m, r = 2, 1
        # (1, 0, 2)
        vis = (1, 0, 2)
        state = _state_from_visible(vis, m, r)
        word = beam_search(m, r, state, self.DEFAULT_POLICY)
        self.assertNotEqual(word, "UNSOLVED")
        self._check_word_sorts(m, r, vis, word)

    def test_sorts_2_2(self):
        """Test a slightly larger instance."""
        m, r = 2, 2
        # (2, 1, 0, 0)
        vis = (2, 1, 0, 0)
        state = _state_from_visible(vis, m, r)
        word = beam_search(m, r, state, self.DEFAULT_POLICY)
        if word != "UNSOLVED":
            self._check_word_sorts(m, r, vis, word)
        # Either a valid word or UNSOLVED (never a false claim)

    def test_deterministic_same_seed_policy(self):
        m, r = 2, 1
        vis = (2, 1, 0)
        state = _state_from_visible(vis, m, r)
        w1 = beam_search(m, r, state, self.DEFAULT_POLICY)
        w2 = beam_search(m, r, state, self.DEFAULT_POLICY)
        self.assertEqual(w1, w2)

    def test_different_weights_may_differ(self):
        m, r = 2, 1
        vis = (0, 1, 2)
        state = _state_from_visible(vis, m, r)
        p1 = {"weights": [10, 1, 1], "beam_width": 5, "max_steps": 100}
        p2 = {"weights": [1, 10, 1], "beam_width": 5, "max_steps": 100}
        w1 = beam_search(m, r, state, p1)
        w2 = beam_search(m, r, state, p2)
        # Both should be valid (not UNSOLVED) or both UNSOLVED — no crash
        for w in (w1, w2):
            if w != "UNSOLVED":
                self._check_word_sorts(m, r, vis, w)

    def test_returns_unsolved_string_when_budget_tiny(self):
        m, r = 3, 2
        vis = (3, 2, 1, 0, 0)
        state = _state_from_visible(vis, m, r)
        p = {"weights": [1, 1, 1], "beam_width": 1, "max_steps": 1}
        word = beam_search(m, r, state, p)
        # With beam_width=1 and max_steps=1, almost certainly can't solve
        self.assertIn(word, {""} | {"UNSOLVED"} | set("LRX"))

    def test_unsolved_never_crashes(self):
        m, r = 5, 3
        vis = (5, 4, 3, 2, 1, 0, 0, 0)
        state = _state_from_visible(vis, m, r)
        p = {"weights": [1, 1, 1], "beam_width": 2, "max_steps": 5}
        word = beam_search(m, r, state, p)
        self.assertIsInstance(word, str)


# ---------------------------------------------------------------------------
# OfflinePolicyProposer
# ---------------------------------------------------------------------------


class TestOfflinePolicyProposer(unittest.TestCase):
    def test_generates_correct_count(self):
        prop = OfflinePolicyProposer(seed=42)
        policies = prop.propose(2, 1, count=7)
        self.assertEqual(len(policies), 7)

    def test_deterministic(self):
        p1 = OfflinePolicyProposer(seed=0).propose(2, 1, count=3)
        p2 = OfflinePolicyProposer(seed=0).propose(2, 1, count=3)
        self.assertEqual(p1, p2)

    def test_different_seeds(self):
        p1 = OfflinePolicyProposer(seed=1).propose(2, 1, count=3)
        p2 = OfflinePolicyProposer(seed=2).propose(2, 1, count=3)
        self.assertNotEqual(p1, p2)

    def test_each_policy_parseable(self):
        prop = OfflinePolicyProposer(seed=7)
        for pol in prop.propose(2, 1, count=10):
            validated = parse_policy(pol)
            self.assertIn("weights", validated)
            self.assertIn("beam_width", validated)
            self.assertIn("max_steps", validated)


# ---------------------------------------------------------------------------
# run_experiment
# ---------------------------------------------------------------------------


class TestRunExperiment(unittest.TestCase):
    def test_returns_json_serialisable_dict(self):
        result = run_experiment(2, 1, mode="baseline", seed=42)
        # Must not raise
        json.dumps(result, allow_nan=False)

    def test_summary_keys(self):
        result = run_experiment(2, 1, mode="baseline", seed=42)
        for key in ("run_id", "m", "r", "mode", "solved", "unsolved", "failures"):
            self.assertIn(key, result)

    def test_baseline_on_canonical_root(self):
        vis = [canonical_root(2, 1)]
        result = run_experiment(2, 1, states=vis, mode="baseline", seed=0)
        # Canonical root is already terminal -> empty word -> SOLVED
        self.assertEqual(result["solved"], 1)

    def test_best_of_n_on_unsorted(self):
        vis = [(2, 1, 0)]
        result = run_experiment(2, 1, states=vis, mode="best_of_n", proposals=3, seed=0)
        # (2,1,0) is sortable in one X step; best_of_n should find it
        self.assertEqual(result["solved"], 1)

    def test_sequential_on_unsorted(self):
        vis = [(0, 1, 2)]
        result = run_experiment(
            2, 1, states=vis, mode="sequential", proposals=3, seed=0
        )
        self.assertEqual(result["solved"], 1)

    def test_parallel_runs_without_error(self):
        vis = [(2, 1, 0), (0, 1, 2)]
        result = run_experiment(2, 1, states=vis, mode="parallel", proposals=2, seed=0)
        self.assertIn("solved", result)

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            run_experiment(2, 1, mode="wrong")

    def test_invalid_m_raises(self):
        with self.assertRaises((ValueError, Exception)):
            run_experiment(0, 1)

    def test_output_file_exclusive_create(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(FileExistsError):
                run_experiment(2, 1, output_file=path)
        finally:
            os.unlink(path)

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.jsonl")
            run_experiment(2, 1, states=[(2, 1, 0)], mode="baseline", output_file=path)
            with open(path) as f:
                lines = f.readlines()
            self.assertGreater(len(lines), 0)
            # Each line must be valid JSON
            for line in lines:
                obj = json.loads(line)
                self.assertIn("result", obj)
                self.assertIn("seed", obj)
                self.assertIn("dataset_hash", obj)
                self.assertIn("code_hash", obj)
                self.assertIn("parent_hash", obj)

    def test_output_file_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.jsonl")
            run_experiment(2, 1, states=[(2, 1, 0)], mode="baseline", output_file=path)
            with open(path) as f:
                rec = json.loads(f.readline())
            # result must be one of the three outcome tags
            self.assertIn(rec["result"], {"SOLVED", "UNSOLVED", "FAILURE"})
            # SOLVED records must have a word
            if rec["result"] == "SOLVED":
                self.assertIsNotNone(rec["word"])
                self.assertIsInstance(rec["word_length"], int)

    def test_result_is_solved_not_failure(self):
        """(2,1,0) must be marked SOLVED, not FAILURE (they are distinct)."""
        result = run_experiment(2, 1, states=[(2, 1, 0)], mode="baseline", seed=0)
        state_rec = result["results"][0]
        self.assertNotEqual(state_rec["result"], "FAILURE")

    def test_custom_proposer(self):
        """Custom proposer object is called."""
        calls = []

        class FakeProposer:
            def propose(self, m, r, count):
                calls.append((m, r, count))
                return [{"weights": [3, 3, 2], "beam_width": 10, "max_steps": 200}]

        run_experiment(
            2, 1, states=[(2, 1, 0)], mode="best_of_n", proposer=FakeProposer()
        )
        self.assertTrue(len(calls) > 0)

    def test_dataset_hash_changes_with_states(self):
        h1 = _dataset_hash([(1, 2, 0)])
        h2 = _dataset_hash([(2, 1, 0)])
        self.assertNotEqual(h1, h2)

    def test_policy_hash_is_deterministic(self):
        p = {"weights": [3, 3, 2], "beam_width": 10, "max_steps": 200}
        self.assertEqual(_policy_hash(p), _policy_hash(dict(p)))


# ---------------------------------------------------------------------------
# ProposalBudget (from provider_adapter — compatibility tests)
# ---------------------------------------------------------------------------


class TestProposalBudget(unittest.TestCase):
    def test_cost_tracking(self):
        b = ProposalBudget(
            max_total_cost=1.0,
            input_cost_per_mtok=0.5,
            output_cost_per_mtok=1.5,
        )
        b.update(input_tokens=1_000_000, output_tokens=500_000)
        # 1M * 0.5/M + 0.5M * 1.5/M = 0.5 + 0.75 = 1.25
        self.assertAlmostEqual(b.estimated_cost(), 1.25, places=6)

    def test_can_afford_request(self):
        b = ProposalBudget(
            max_total_cost=1.0,
            input_cost_per_mtok=0.5,
            output_cost_per_mtok=1.5,
        )
        self.assertTrue(b.can_afford_request(est_tokens=1000))
        b.update(input_tokens=1_000_000, output_tokens=500_000)
        self.assertFalse(b.can_afford_request(est_tokens=1_000_000))

    def test_offline_mode(self):
        b = ProposalBudget(max_total_cost=None)
        self.assertFalse(b.can_afford_request())


# ---------------------------------------------------------------------------
# OfflineMockProposer (from provider_adapter — compatibility tests)
# ---------------------------------------------------------------------------


class TestOfflineMockProposer(unittest.TestCase):
    def test_generates_words(self):
        p = OfflineMockProposer(m=2, r=1, seed=42)
        words = p.propose_words(count=5)
        self.assertEqual(len(words), 5)
        for w in words:
            self.assertTrue(all(c in "LRX" for c in w))

    def test_deterministic(self):
        w1 = OfflineMockProposer(m=2, r=1, seed=99).propose_words(3)
        w2 = OfflineMockProposer(m=2, r=1, seed=99).propose_words(3)
        self.assertEqual(w1, w2)


if __name__ == "__main__":
    unittest.main()
