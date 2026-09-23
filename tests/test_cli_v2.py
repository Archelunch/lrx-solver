import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.lrx.cli import main
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, json.loads(out.getvalue() or err.getvalue())


class CliV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_table_verify_and_build(self):
        code, out = run_cli("table", "verify")
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_cli("table", "build", "4", "2", "--out", tmp)
            self.assertEqual((code, out["status"], out["radius"]), (0, "COMPLETE", 12))
            code, out = run_cli(
                "table", "build", "12", "4", "--out", tmp, "--max-bytes", "1000"
            )
            self.assertEqual((code, out["status"]), (2, "INCOMPLETE"))

    def test_eval_and_feedback(self):
        path = str(ROOT / "candidates/baselines/bound_trivial.json")
        code, out = run_cli("eval", path)
        self.assertEqual(code, 0)
        self.assertTrue(out["valid"])
        self.assertIn("graphs", out)
        code, out = run_cli("eval", path, "--feedback")
        self.assertEqual(out["kind"], "bound")

    def test_certify_features_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            cand = Path(tmp) / "c.json"
            cand.write_text(json.dumps({"kind": "bound", "expr": 3}))
            code, out = run_cli("certify", str(cand), "4", "2")
            self.assertEqual(code, 1)
            self.assertFalse(out["holds_on_graph"])
        code, out = run_cli("features", "3", "2", "--v", "3,0,1,2,0")
        self.assertEqual(out["cinv"], 0)
        code, out = run_cli("prompt", str(ROOT / "campaigns/grok-rules-adaevolve.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["messages"][0]["role"], "system")

    def test_live_commands_refuse_without_flag(self):
        cfg = str(ROOT / "campaigns/grok-smoke.json")
        code, out = run_cli("llm-smoke", cfg)
        self.assertEqual(code, 2)
        self.assertIn("allow-network", out["reason"])
        code, out = run_cli("evolve", cfg, "--run-dir", str(self.data.base / "nope"))
        self.assertEqual(code, 2)
        self.assertFalse((self.data.base / "nope").exists())

    def test_campaign_configs_are_well_formed(self):
        from src.lrx.candidates import Candidate
        from src.lrx.evolve import DEFAULTS

        for path in (ROOT / "campaigns").glob("*.json"):
            cfg = json.loads(path.read_text())
            self.assertFalse(set(cfg) - set(DEFAULTS) - {"name", "description"}, path)
            for seed in cfg.get("seeds", []):
                self.assertIn(
                    Candidate(json.loads((ROOT / seed).read_text())).kind, cfg["kinds"]
                )
            provider = cfg.get("provider", {})
            if provider.get("type") == "openai_compatible":
                self.assertLessEqual(provider["max_spend_usd"], 5)
                self.assertGreater(provider["input_usd_per_mtok"], 0)


if __name__ == "__main__":
    unittest.main()


class LeaderboardTests(unittest.TestCase):
    def test_mixed_summary_schemas(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "ours"
            b = Path(tmp) / "gepa"
            a.mkdir()
            b.mkdir()
            (a / "summary.json").write_text(
                json.dumps(
                    {
                        "engine": "gepa",
                        "best": {"score": -5.0, "hash": "h"},
                        "usage": {"estimated_usd": 0.1},
                    }
                )
            )
            (b / "summary.json").write_text(
                json.dumps(
                    {
                        "engine": "gepa-official",
                        "best": "{json text}",
                        "best_train_score": -9.0,
                        "usd": 0.2,
                    }
                )
            )
            code, out = run_cli("leaderboard", "--runs", tmp)
            self.assertEqual(code, 0)
            self.assertEqual([r["best_score"] for r in out["runs"]], [-5.0, -9.0])
