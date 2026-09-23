"""Search contracts stay aligned without broadening the trusted candidate DSL."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.lrx.evolve import Campaign
from src.lrx.proposers import LLMProposer, edit_violation


class ReflectionContractTests(unittest.TestCase):
    def test_campaign_kinds_reach_reflector_and_restrict_candidate_shapes(self):
        campaign = object.__new__(Campaign)
        campaign.cfg = {"kinds": ["rules"], "select": "score", "max_proposals": 8}
        campaign.proposals = 4
        campaign.archive = lambda: []
        campaign.ranked = lambda pool: pool
        campaign.recent_attempts = lambda count: []
        campaign.insights = []
        campaign.strategy = {}
        campaign.strategy_history = []
        campaign.population = lambda: {}
        summary = campaign.reflection_summary("strategy")
        self.assertEqual(summary["allowed_kinds"], ["rules"])
        client = Mock()
        client.complete.return_value = {"text": "{}", "cost_usd": 0,
                                        "tokens_in": 1, "tokens_out": 1, "seconds": 0}
        out = LLMProposer(client).reflect(summary, task="strategy")
        system = out["messages"][0]["content"]
        self.assertIn('Allowed candidate kinds: ["rules"]', system)
        self.assertIn('"kind":"rules"', system)
        self.assertNotIn('"kind":"potential"', system)
        self.assertNotIn('"kind":"bound"', system)


class FinishingGuardTests(unittest.TestCase):
    def test_real_insertion_rule_can_change_but_finisher_cannot(self):
        root = Path(__file__).resolve().parents[1]
        parent = json.loads((root / "candidates/leads/49ab346cb44b2f1b.json").read_text())
        child = copy.deepcopy(parent)
        child["rules"][3]["do"] = "R"
        self.assertIsNone(edit_violation(parent, child))
        child = copy.deepcopy(parent)
        child["rules"][2]["do"] = "R"
        self.assertIn("finishing", edit_violation(parent, child))

    def test_only_provably_unsorted_conditions_are_exempt(self):
        cases = [
            (["not", "csorted"], True),
            (["eq", 0, "csorted"], True),
            (["ne", "csorted", 1], True),
            (["and", ["eq", "csorted", 0], ["eq", "a", 1]], True),
            (["or", ["not", "csorted"], ["eq", "csorted", 0]], True),
            (["or", ["not", "csorted"], ["eq", "a", 1]], False),
            (["and", "csorted", ["eq", "a", 1]], False),
            (["lt", "csorted", 1], False),  # unsupported inference stays conservative
        ]
        for condition, allowed in cases:
            with self.subTest(condition=condition):
                parent = {"kind": "rules", "rules": [{"if": condition, "do": "L"}], "default": "R"}
                child = copy.deepcopy(parent)
                child["rules"][0]["do"] = "X"
                self.assertEqual(edit_violation(parent, child) is None, allowed)


class RatioFocusTests(unittest.TestCase):
    def campaign(self, sanity_failures=0):
        campaign = object.__new__(Campaign)
        campaign.cfg = {"select": "ratio"}
        graphs = [{"graph": "m4r2", "m": 4, "T": 12, "value_max": 21,
                   "feedback": True, "failures": sanity_failures}]
        graphs.extend({"graph": name, "m": m, "T": target, "value_max": value,
                       "feedback": True, "failures": 0}
                      for name, m, target, value in (("m8r2", 8, 42, 63),
                                                   ("m8r3", 8, 48, 75),
                                                   ("m9r2", 9, 52, 76)))
        campaign.records = [{"eval": {"graphs": graphs}}]
        campaign.archive = lambda: campaign.records
        return campaign

    def test_full_batch_repeats_target_instead_of_focusing_passed_sanity(self):
        campaign = self.campaign()
        self.assertEqual(campaign.focus_for(0, {"m8r2", "m8r3", "m9r2"})["graph"], "m8r3")

    def test_sanity_failure_is_still_eligible_for_repair(self):
        self.assertEqual(self.campaign(1).focus_for(0, set())["graph"], "m4r2")
