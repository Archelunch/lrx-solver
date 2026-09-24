"""Focused tests for development evidence selection and provenance."""

import json
import tempfile
import unittest
from pathlib import Path

from integrations.research_archive import DevelopmentArchive


CASE = "k5-mask302-order15713"
DUAL = {"tight": [1, 2, 3, 4], "mu": ["11/14", "197/196", "1/8", "261/392"],
        "nu": "30221/392"}


def trace(status="NO_CERTIFICATE", *, base=80, word="L"):
    return {"case": {"id": CASE, "mask": 302, "blocks": 5}, "status": status,
            "accepted_words": [{"raw_word": word, "profile": {
                "base": base, "gamma": [0, 8, 11, 9, 3], "word": word}}],
            "rejected_words": [], "lp": {"base": "24149/392"}}


class ArchiveProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.archive = DevelopmentArchive(Path(self.temp.name) / "development.sqlite")

    def tearDown(self):
        self.archive.close()
        self.temp.cleanup()

    def add(self, source, *, run="round", score=1, traces=None, parent_id=None, role=None):
        return self.archive.add(run_id=run, engine="gepa", source=source, score=score,
                                feedback={"reason": "hard case unresolved"},
                                traces=traces if traces is not None else [trace()],
                                provenance={"role": role} if role else {}, parent_id=parent_id)

    def test_unknown_parent_is_explicit_and_known_parent_has_real_diff(self):
        first = self.add("def p():\n return 'L'\n", role="incumbent")
        root = self.archive.get(first)
        self.assertEqual(root["lineage_status"], "unknown_parent")
        self.assertEqual(root["source_diff"], "")
        child = self.add("def p():\n return 'R'\n", parent_id=first)
        self.assertEqual(self.archive.get(child)["lineage_status"], "known_parent")
        self.assertIn("+ return 'R'", self.archive.get(child)["source_diff"])

    def test_duplicate_seed_rows_do_not_displace_distinct_failure(self):
        seed = "def p():\n return 'L'\n"
        first = self.add(seed, score=2015, role="incumbent")
        for index in range(12):
            self.add(seed, run=f"one-case-{index}", score=1001)
        novel = self.add("def p():\n return 'R'\n", score=1,
                         traces=[trace(base=79, word="R")])
        rows = self.archive.search(case_id=CASE, limit=10, objective="novelty")
        self.assertEqual(len(rows), 2)
        selected = self.archive.select_context(CASE, limit=2, max_chars=6000,
                                               dual=DUAL, incumbent_source_sha256=self.archive.get(first)["source_sha256"])
        self.assertEqual({row["source_sha256"] for row in selected["selected"]},
                         {self.archive.get(first)["source_sha256"], self.archive.get(novel)["source_sha256"]})
        self.assertLessEqual(selected["chars"], 6000)
        self.assertIn("NO_CERTIFICATE", selected["text"])
        self.assertIn('"source_diff_excerpt": ""', selected["text"])

    def test_complementarity_uses_exact_dual_not_mixed_raw_score(self):
        first = self.add("seed", score=2015, role="incumbent")
        worse = self.add("worse", score=999999, traces=[trace(base=90, word="W")])
        better = self.add("better", score=-4, traces=[trace(base=60, word="B")])
        selected = self.archive.select_context(CASE, limit=2, dual=DUAL,
                                               incumbent_source_sha256=self.archive.get(first)["source_sha256"])
        self.assertEqual(selected["selected"][1]["id"], better)
        self.assertNotEqual(selected["selected"][1]["id"], worse)
        payload = json.loads(selected["text"])
        self.assertEqual(payload["examples"][1]["reduced_cost_scope"],
                         "frozen_development_finite_pool_filter")

    def test_context_is_bounded_and_case_specific(self):
        first = self.add("X" * 10000, role="incumbent")
        self.add("Y" * 10000, traces=[{"case": {"id": "other"}, "status": "INVALID_OUTPUT"}])
        selected = self.archive.select_context(CASE, limit=2, max_chars=1600,
                                               incumbent_source_sha256=self.archive.get(first)["source_sha256"])
        self.assertEqual(len(selected["selected"]), 1)
        self.assertLessEqual(selected["chars"], 1600)
        self.assertEqual(selected["chars"], len(selected["text"]))
        self.assertEqual(json.loads(selected["text"])["examples"][0]["source_total_chars"], 10000)


if __name__ == "__main__":
    unittest.main()
