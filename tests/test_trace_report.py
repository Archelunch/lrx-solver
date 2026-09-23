import contextlib
import io
import json
import unittest
from pathlib import Path

from src.lrx import prompt, trace
from src.lrx.commands import _follow
from src.lrx.evolve import Campaign
from src.lrx.proposers import OfflineMutator
from src.lrx.report import write_report
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]
SEED = str(ROOT / "candidates/baselines/rules_bubble.json")


class PromptingMutator(OfflineMutator):
    """Offline mutator that also returns the messages an LLM would receive."""

    def propose(self, mode, parents, kinds, insights=None, seed=0):
        out = super().propose(mode, parents, kinds, insights, seed)
        out["messages"] = prompt.messages("task", parents, kinds, insights)
        out["text"] = "reply " + str(seed)
        return out


class TraceReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()
        cfg = {
            "name": "t",
            "engine": "adaevolve",
            "kinds": ["rules"],
            "seeds": [SEED],
            "max_proposals": 6,
            "batch": 3,
            "eval_workers": 2,
            "islands": 2,
            "stagnation": 3,
            "seed": 2,
        }
        cls.run_dir = cls.data.base / "run"
        Campaign(cfg, cls.run_dir, PromptingMutator(2)).run()
        gcfg = dict(cfg, engine="gepa")
        cls.run2 = cls.data.base / "run2"
        Campaign(gcfg, cls.run2, PromptingMutator(3)).run()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_logs_prompts_evals_batches(self):
        run = trace.load_run(self.run_dir)
        self.assertTrue(run["complete"])
        self.assertEqual(len(run["batches"]), 2)
        self.assertIn("islands", run["batches"][-1])
        proposals = [c for c in run["candidates"] if c["mode"] != "seed"]
        self.assertTrue(all(c.get("prompt_system_sha") for c in proposals))
        self.assertTrue(
            all(c["prompt_messages"][0]["role"] == "user" for c in proposals)
        )
        sha = proposals[0]["prompt_system_sha"]
        system = (self.run_dir / "prompts" / f"system-{sha}.txt").read_text()
        self.assertEqual(system, prompt.system_prompt(["rules"]))
        self.assertTrue(list((self.run_dir / "evals").glob("*.json")))
        gepa = trace.load_run(self.run2)
        self.assertIn("front", gepa["batches"][-1])

    def test_trace_views(self):
        run = trace.load_run(self.run_dir)
        lines = trace.lineage_lines(run)
        self.assertEqual(len(lines), len(run["candidates"]))
        self.assertTrue(lines[0].startswith("#0"))
        rows = trace.timeline_rows(run)
        self.assertEqual([r["proposals"] for r in rows], [3, 6])
        c = trace.candidate_trace(run, 0)
        self.assertIn("eval", c)
        self.assertEqual(trace.overview(run)["candidates"], 7)
        best = trace.best_so_far(run)
        self.assertEqual(len(best), 7)
        self.assertTrue(all(b is not None for _, b in best))

    def test_follow_stops_at_end(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = _follow(self.run_dir / "events.jsonl", poll=0.01, idle_limit=1)
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("batch 0", text)
        self.assertTrue(text.strip().endswith("end"))

    def test_reports(self):
        path, size = write_report([self.run_dir], self.data.base / "r.html")
        doc = Path(path).read_text()
        self.assertGreater(size, 10_000)
        for needle in (
            'id="outcome"',
            'id="lineage"',
            'id="heldout"',
            "<svg",
            "Prompt (user part)",
            "Model reply",
            "--accent:",
            "prefers-color-scheme: dark",
        ):
            self.assertIn(needle, doc)
        self.assertNotIn("{{", doc)
        path, _ = write_report([self.run_dir, self.run2], self.data.base / "c.html")
        doc = Path(path).read_text()
        self.assertIn("Campaign comparison", doc)
        self.assertEqual(doc.count('class="row"><td class="step">'), 2)

    def test_report_escapes_model_text(self):
        events = self.run_dir / "events.jsonl"
        lines = events.read_text().splitlines()
        evil = json.loads(lines[2])
        self.assertEqual(evil["event"], "candidate")
        evil["model_text"] = "<script>alert(1)</script>"
        copy = self.data.base / "evil"
        copy.mkdir()
        (copy / "events.jsonl").write_text(
            "\n".join([lines[0], json.dumps(evil)]) + "\n"
        )
        doc = Path(write_report([copy], copy / "r.html")[0]).read_text()
        self.assertNotIn("<script>alert(1)</script>", doc)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", doc)


if __name__ == "__main__":
    unittest.main()
