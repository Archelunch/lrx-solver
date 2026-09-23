import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.lrx.candidates import Candidate
from src.lrx.evolve import Campaign, run_campaign
from src.lrx.llm import ChatClient, SpendLedger
from src.lrx.proposers import (
    LLMProposer,
    OfflineMutator,
    edit_violation,
    rule_edits,
)
from tests.fixtures import TinyData
from tests.test_llm_campaign import _chat, _response

ROOT = Path(__file__).resolve().parents[1]
SEED = str(ROOT / "candidates/baselines/rules_bubble.json")
LEAD = json.loads((ROOT / "candidates/leads/1ea0a8de58e2fa16.json").read_text())


def _reply(spec):
    return _chat("```json\n" + json.dumps(spec) + "\n```")


class RuleEditTests(unittest.TestCase):
    def test_counts(self):
        child = copy.deepcopy(LEAD)
        self.assertEqual(rule_edits(LEAD, child), 0)
        child["rules"][6]["do"] = "R"
        self.assertEqual(rule_edits(LEAD, child), 1)
        child["rules"].insert(0, {"if": ["eq", "a", 1], "do": "X"})
        self.assertEqual(rule_edits(LEAD, child), 2)
        child["default"] = "L"
        self.assertEqual(rule_edits(LEAD, child), 3)
        swapped = copy.deepcopy(LEAD)
        swapped["rules"][4], swapped["rules"][5] = (
            swapped["rules"][5],
            swapped["rules"][4],
        )
        self.assertEqual(rule_edits(LEAD, swapped), 2)
        shorter = copy.deepcopy(LEAD)
        shorter["rules"].pop()
        self.assertEqual(rule_edits(LEAD, shorter), 1)

    def test_violation_messages(self):
        child = copy.deepcopy(LEAD)
        child["rules"][6]["do"] = "R"
        child["rules"][7]["do"] = "L"
        self.assertIsNone(edit_violation(LEAD, child))
        child["rules"][8]["do"] = "L"
        self.assertIn("at most 2", edit_violation(LEAD, child))
        finish = copy.deepcopy(LEAD)
        finish["rules"][3]["do"] = "L"
        self.assertIn("csorted", edit_violation(LEAD, finish))
        self.assertIsNone(
            edit_violation({"kind": "bound", "expr": 1}, {"kind": "bound", "expr": 2})
        )


class OfflineEditTests(unittest.TestCase):
    def test_offline_edit_stays_within_limit(self):
        for seed in range(30):
            out = OfflineMutator(seed).propose("edit", [(LEAD, {})], ["rules"], seed)
            Candidate(out["spec"])
            self.assertIsNone(edit_violation(LEAD, out["spec"]), seed)


class LLMEditTests(unittest.TestCase):
    def client(self):
        return ChatClient(
            "https://api.example.com/v1",
            "m",
            SpendLedger(1, 1, 1, 5),
            allow_network=True,
        )

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_rewrite_is_rejected_then_repaired(self, opener):
        rewrite = json.loads(Path(SEED).read_text())
        edit = copy.deepcopy(LEAD)
        edit["rules"][6]["do"] = "R"
        second = _response(_reply(edit))
        opener.side_effect = [_response(_reply(rewrite)), second]
        out = LLMProposer(self.client(), repairs=1).propose(
            "edit", [(LEAD, {})], ["rules"], seed=1
        )
        self.assertIsNone(out["error"])
        self.assertEqual(out["spec"], edit)
        self.assertIn("at most 2", out["attempts"][0]["error"])
        sent = json.loads(second.open.call_args[0][0].data)["messages"]
        self.assertIn("at most 2", sent[-1]["content"])
        task = sent[1]["content"]
        self.assertIn("at most 2 rule changes", task)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_unrepaired_rewrite_is_not_scored(self, opener):
        rewrite = json.loads(Path(SEED).read_text())
        opener.side_effect = [_response(_reply(rewrite)), _response(_reply(rewrite))]
        out = LLMProposer(self.client(), repairs=1).propose(
            "edit", [(LEAD, {})], ["rules"], seed=1
        )
        self.assertIsNone(out["spec"])
        self.assertIn("at most 2", out["error"])


class EditCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def cfg(self, engine, **kw):
        return {
            "name": f"edit-{engine}",
            "engine": engine,
            "kinds": ["rules"],
            "seeds": [SEED],
            "max_proposals": 6,
            "batch": 3,
            "eval_workers": 2,
            "islands": 2,
            "seed": 3,
            "refine_mode": "edit",
            **kw,
        }

    def test_bad_values(self):
        with self.assertRaises(ValueError):
            Campaign(
                self.cfg("sequential", refine_mode="x"), self.data.base / "b1", None
            )
        with self.assertRaises(ValueError):
            Campaign(
                self.cfg("sequential", explore_max=1.5), self.data.base / "b2", None
            )

    def test_sequential_edit_campaign(self):
        run_dir = self.data.base / "edit-seq"
        summary = run_campaign(self.cfg("sequential"), run_dir)
        self.assertEqual(summary["proposals"], 6)
        events = [
            json.loads(line)
            for line in (run_dir / "events.jsonl").read_text().splitlines()
        ]
        cands = [e for e in events if e["event"] == "candidate" and e["mode"] != "seed"]
        self.assertEqual({e["mode"] for e in cands}, {"edit"})
        specs = {e["id"]: e["spec"] for e in events if e["event"] == "candidate"}
        for e in cands:
            if e["spec"]:
                parent = specs[e["parents"][0]]
                self.assertLessEqual(rule_edits(parent, e["spec"]), 2)

    def test_adaevolve_explore_cap(self):
        run_dir = self.data.base / "edit-ada"
        run_campaign(self.cfg("adaevolve", explore_max=0.3, max_proposals=9), run_dir)
        batches = [
            json.loads(line)
            for line in (run_dir / "events.jsonl").read_text().splitlines()
            if '"event": "batch"' in line
        ]
        reqs = [r for b in batches for r in b["requests"]]
        self.assertEqual(len(reqs), 9)
        self.assertTrue(all(r["explore_p"] <= 0.3 for r in reqs))
        self.assertTrue(all(r["mode"] in ("explore", "edit") for r in reqs))


if __name__ == "__main__":
    unittest.main()
