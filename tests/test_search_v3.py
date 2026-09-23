"""Search v3: async steady state, proposal context, tactics, GEPA P x N,
AdaEvolve formulas, EvoX strategies, potential descent feedback (offline)."""

import json
import math
import unittest
from pathlib import Path

from src.lrx import evaluator, prompt
from src.lrx.evolve import EVOX_START, Campaign, parse_tactics, validate_strategy
from src.lrx.feedback import MAX_BYTES, compress, descent_detail
from src.lrx.proposers import (
    STRATEGY_SYSTEM,
    TACTICS_SYSTEM,
    LLMProposer,
    OfflineMutator,
)
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]
SEED = str(ROOT / "candidates/baselines/rules_bubble.json")
POTENTIAL = {"kind": "potential", "expr": ["add", "inv", "zeros_in_prefix"]}


class RecordingMutator(OfflineMutator):
    """Offline mutator that keeps the context each request received."""

    def __init__(self, seed=0):
        super().__init__(seed)
        self.contexts = []

    def propose(self, mode, parents, kinds, insights=None, seed=0, context=None):
        self.contexts.append(context)
        out = super().propose(mode, parents, kinds, insights, seed, context)
        out["messages"] = prompt.messages("task", parents, kinds, insights, context)
        return out


def _events(run_dir, kind=None):
    rows = [json.loads(x) for x in (run_dir / "events.jsonl").read_text().splitlines()]
    return [e for e in rows if kind is None or e["event"] == kind]


class StrategyParsingTests(unittest.TestCase):
    def test_validate_strategy(self):
        s, err = validate_strategy(EVOX_START)
        self.assertIsNone(err)
        self.assertEqual(s["modes"], {"exploit": 1.0})
        s, err = validate_strategy({"parent": "front", "modes": {"merge": 1}})
        self.assertIsNone(err)
        self.assertEqual(s["history"], EVOX_START["history"])
        for bad in (
            [],
            {"parent": "worst"},
            {"modes": {}},
            {"modes": {"exploit": -1}},
            {"modes": {"exploit": True}},
            {"modes": {"mutate": 1}},
            {"history": 9},
            {"inspirations": "2"},
            {"focus": 1},
            {"tactic": "x" * 801},
            {"code": "import os"},
        ):
            self.assertIsNone(validate_strategy(bad)[0], bad)

    def test_parse_tactics(self):
        text = 'why\n```json\n[{"idea": "a", "how": "b"}, {"how": "no idea"}]\n```'
        self.assertEqual(parse_tactics(text), [{"idea": "a", "how": "b"}])
        self.assertEqual(
            parse_tactics('{"tactics": [{"idea": "c", "target": "m8r3"}]}'),
            [{"idea": "c", "target": "m8r3"}],
        )
        self.assertEqual(parse_tactics("no json here"), [])
        many = json.dumps([{"idea": str(i)} for i in range(9)])
        self.assertEqual(len(parse_tactics(many)), 4)


class PromptContextTests(unittest.TestCase):
    def test_user_prompt_sections(self):
        ctx = {
            "tactic": {"idea": "use r0 as a pass counter", "cautions": "keep finish"},
            "focus": {"graph": "m8r3", "parent_score": -40, "archive_best": -30},
            "inspirations": [{"id": 3, "score": -1, "spec": {"kind": "rules"}}],
            "history": [
                {"id": i, "status": "discard", "notes": "n" * 500} for i in range(40)
            ],
        }
        text = prompt.user_prompt(
            "Improve.", [({"kind": "rules"}, {})], None, ["rules"], ctx
        )
        for needle in (
            "BREAKTHROUGH IDEA - IMPLEMENT THIS: use r0 as a pass counter",
            "Cautions: keep finish",
            "Focus graph: m8r3",
            "Other archive members",
            "Recent attempts, newest first",
        ):
            self.assertIn(needle, text)
        self.assertLess(text.index("BREAKTHROUGH"), text.index("Parent 1"))
        self.assertLess(len(text), 2 * prompt.MAX_CONTEXT_CHARS + 2000)
        self.assertEqual(
            prompt.user_prompt("t", [], None, ["rules"]),
            prompt.user_prompt("t", [], None, ["rules"], {}),
        )

    def test_llm_proposer_passes_context_and_reflect_tasks(self):
        class Client:
            def __init__(self):
                self.seen = []

            def complete(self, messages):
                self.seen.append(messages)
                return {
                    "text": '```json\n{"kind": "rules", "rules": [{"if": 1, "do": "L"}], "default": "L"}\n```',
                    "cost_usd": 0.0,
                    "seconds": 0.0,
                    "tokens_in": 1,
                    "tokens_out": 1,
                }

        client = Client()
        proposer = LLMProposer(client)
        ctx = {"tactic": {"idea": "zz-idea"}}
        out = proposer.propose(
            "exploit", [({"kind": "rules"}, {})], ["rules"], context=ctx
        )
        self.assertIsNone(out["error"])
        self.assertIn("zz-idea", client.seen[0][1]["content"])
        proposer.reflect({"x": 1}, task="strategy")
        self.assertTrue(client.seen[-1][0]["content"].startswith(STRATEGY_SYSTEM))
        proposer.reflect({"x": 1}, task="tactics")
        self.assertTrue(client.seen[-1][0]["content"].startswith(TACTICS_SYSTEM))


class CampaignV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def cfg(self, engine, **kw):
        return {
            "name": f"v3-{engine}",
            "engine": engine,
            "kinds": ["rules"],
            "seeds": [SEED],
            "max_proposals": 8,
            "batch": 3,
            "eval_workers": 2,
            "islands": 2,
            "seed": 5,
            **kw,
        }

    def run_cfg(self, name, cfg, proposer=None):
        run_dir = self.data.base / name
        campaign = Campaign(cfg, run_dir, proposer or RecordingMutator(cfg["seed"]))
        return campaign, campaign.run(), run_dir

    def test_bad_values(self):
        for i, kw in enumerate(
            (
                {"gepa_n": 0},
                {"history": 13},
                {"window": 1.5},
                {"merge_prob": 2},
                {"strategy": {"parent": "x"}},
            )
        ):
            engine = "evox" if "strategy" in kw else "gepa"
            with self.assertRaises(ValueError):
                Campaign(self.cfg(engine, **kw), self.data.base / f"bad{i}", None)

    def test_async_sequential_with_history(self):
        proposer = RecordingMutator(1)
        cfg = self.cfg("sequential", **{"async": True, "history": 3, "inspirations": 1})
        campaign, summary, run_dir = self.run_cfg("async-seq", cfg, proposer)
        self.assertEqual(summary["proposals"], 8)
        cands = [e for e in _events(run_dir, "candidate") if e["mode"] != "seed"]
        self.assertEqual(len(cands), 8)
        self.assertEqual(sorted(e["proposal"] for e in cands), list(range(1, 9)))
        batches = _events(run_dir, "batch")
        self.assertEqual(len(batches), 8)
        self.assertTrue(all(len(b["requests"]) == 1 for b in batches))
        self.assertTrue(all(b["inflight"] <= 2 for b in batches))
        # The first requests see no history yet; later ones see at most 3 attempts.
        self.assertIsNone(proposer.contexts[0])
        later = [c for c in proposer.contexts if c and "history" in c]
        self.assertTrue(later)
        self.assertTrue(all(len(c["history"]) <= 3 for c in later))
        self.assertTrue(all(h["mode"] != "seed" for c in later for h in c["history"]))
        self.assertEqual(summary["stop_reason"], "max_proposals")

    def test_gepa_pxn_focus_and_merge_cap(self):
        cfg = self.cfg(
            "gepa", batch=4, gepa_n=2, focus=True, max_merges=1, max_proposals=12
        )
        campaign, summary, run_dir = self.run_cfg("gepa-pxn", cfg)
        self.assertLessEqual(summary["merges"], 1)
        for b in _events(run_dir, "batch"):
            refine = [r for r in b["requests"] if r["mode"] != "merge"]
            by_parent = {}
            for r in refine:
                by_parent.setdefault(tuple(r["parents"]), []).append(r["focus"])
            for foci in by_parent.values():
                if len(by_parent) > 1:
                    self.assertLessEqual(len(foci), 2)
                named = [f for f in foci if f]
                self.assertEqual(len(named), len(set(named)))
        merges = [e for e in _events(run_dir, "candidate") if e["mode"] == "merge"]
        if merges:
            first = min(e["proposal"] for e in merges)
            kept = [
                e
                for e in _events(run_dir, "candidate")
                if e["status"] == "keep" and e["mode"] != "seed"
            ]
            self.assertTrue(any(e["proposal"] < first for e in kept))

    def test_potential_archive_falls_back_to_sanity_stopped(self):
        seed = str(ROOT / "candidates/baselines/potential_naive.json")
        cfg = self.cfg(
            "gepa", kinds=["potential"], seeds=[seed], focus=True, max_proposals=3
        )
        campaign, _, run_dir = self.run_cfg("pot-gepa", cfg)
        self.assertTrue(campaign.records[0]["eval"].get("stopped"))
        self.assertIn(0, campaign.pareto_front())
        first = _events(run_dir, "batch")[0]["requests"]
        self.assertTrue(all(r["focus"] for r in first))
        self.assertIn("descent_detail", campaign.records[0]["feedback"])

    def test_select_failures_ranks_fewer_failing_states_first(self):
        with self.assertRaises(ValueError):
            Campaign(self.cfg("gepa", select="best"), self.data.base / "bad-sel", None)

        def rec(i, score, fails, stopped=True):
            graphs = [
                {"graph": g, "feedback": True, "failures": f}
                for g, f in zip(("a", "b"), fails)
            ]
            graphs.append({"graph": "held", "feedback": False, "failures": 99})
            return {
                "id": i,
                "valid": True,
                "score": score,
                "instances": {"a": score, "b": score},
                "eval": {"graphs": graphs, "stopped": stopped},
            }

        campaign = Campaign(
            self.cfg("gepa", select="failures"), self.data.base / "sel", None
        )
        campaign.records = [
            rec(0, -10, (5, 5)),
            rec(1, -50, (1, 6)),
            rec(2, -20, (4, 2)),
        ]
        self.assertEqual(Campaign.failures(campaign.records[1]), 7)
        self.assertEqual(
            [r["id"] for r in campaign.ranked(campaign.records)], [2, 1, 0]
        )
        self.assertEqual(set(campaign.pareto_front()), {1, 2})
        focus = campaign.focus_for(1, set())
        self.assertEqual(
            focus, {"graph": "b", "parent_failures": 6, "archive_fewest": 2}
        )
        text = prompt.user_prompt("t", [], None, ["potential"], {"focus": focus})
        self.assertIn("6 failing states there, fewest in the archive 2", text)
        # A candidate that passes sanity outranks any stopped one.
        campaign.records.append(rec(3, -900, (9, 9), stopped=False))
        self.assertEqual(campaign.ranked(campaign.records)[0]["id"], 3)
        scored = Campaign(self.cfg("gepa"), self.data.base / "sel2", None)
        scored.records = campaign.records[:3]
        self.assertEqual([r["id"] for r in scored.ranked(scored.records)], [0, 2, 1])
        for c in (campaign, scored):
            c._events.close()
            c._tsv.close()

    def test_select_failures_potential_run(self):
        seed = str(ROOT / "candidates/baselines/potential_naive.json")
        cfg = self.cfg(
            "gepa",
            kinds=["potential"],
            seeds=[seed],
            focus=True,
            select="failures",
            max_proposals=4,
        )
        campaign, summary, run_dir = self.run_cfg("pot-sel", cfg)
        self.assertEqual(summary["proposals"], 4)
        best = campaign.records[campaign.best_id]
        self.assertEqual(
            max(campaign.rank(r) for r in campaign.archive()), campaign.rank(best)
        )
        self.assertEqual(summary["heldout"][0]["id"], campaign.best_id)
        first = _events(run_dir, "batch")[0]["requests"]
        self.assertTrue(all(r["focus"] for r in first))

    def test_adaevolve_paper_formulas(self):
        cfg = self.cfg("adaevolve", explore_max=0.7, max_proposals=6)
        campaign, _, run_dir = self.run_cfg("ada", cfg)
        for b in _events(run_dir, "batch"):
            for r in b["requests"]:
                self.assertGreaterEqual(r["explore_p"], 0.1 - 1e-9)
                self.assertLessEqual(r["explore_p"], 0.7 + 1e-9)
        for G, expected in (
            (0.0, 0.7),
            (1e6, 0.1 + 0.6 / 1001),
            (0.25, 0.1 + 0.6 / 1.5),
        ):
            for s in campaign.islands:
                s["G"] = G
            self.assertAlmostEqual(
                campaign.plan_adaevolve([])["explore_p"], expected, places=3
            )
        state = campaign.islands[0]
        before = state["visits"]
        campaign.update_island(0, campaign.records[0])
        self.assertAlmostEqual(state["visits"], 0.9 * before + 1.0)
        self.assertAlmostEqual(campaign.cfg["ucb_c"], math.sqrt(2))

    def test_tactics_are_tracked(self):
        cfg = self.cfg(
            "sequential",
            tactics=True,
            stagnation=2,
            tactic_trials=1,
            batch=2,
            max_proposals=12,
        )
        proposer = RecordingMutator(7)
        _, summary, run_dir = self.run_cfg("tactics", cfg, proposer)
        refl = [e for e in _events(run_dir, "reflection") if e["task"] == "tactics"]
        self.assertTrue(refl)
        self.assertTrue(all(e.get("tactics") for e in refl))
        tactics = summary["tactics"]
        self.assertTrue(tactics)
        for t in tactics:
            self.assertLessEqual(t["trials"], 1 + t["wins"])
            self.assertEqual(len(t["outcomes"]), t["trials"])
        carried = [
            e for e in _events(run_dir, "candidate") if e.get("tactic") is not None
        ]
        self.assertTrue(carried)
        self.assertTrue(
            any(
                c and c.get("tactic", {}).get("how") == "offline"
                for c in proposer.contexts
            )
        )

    def test_evox_windows_and_strategy_changes(self):
        cfg = self.cfg("evox", window=2, batch=2, max_proposals=10)
        campaign, summary, run_dir = self.run_cfg("evox", cfg)
        windows = _events(run_dir, "strategy_window")
        self.assertGreaterEqual(len(windows), 4)
        for w in windows:
            expected = w["delta"] / (abs(w["start"]) + 1) / math.sqrt(2)
            self.assertAlmostEqual(w["J"], round(expected, 6), places=5)
        refl = [e for e in _events(run_dir, "reflection") if e["task"] == "strategy"]
        stalled = [w for w in windows if w["delta"] <= 0 and w["proposals"] < 10]
        self.assertEqual(len(refl) > 0, len(stalled) > 0)
        self.assertEqual(summary["strategy_history"][0]["strategy"]["parent"], "best")
        fresh = Campaign(cfg, self.data.base / "evox-apply", RecordingMutator(1))
        current = dict(fresh.strategy)
        fresh.apply_reflection("strategy", {"text": '{"parent": "nowhere"}'})
        self.assertEqual(fresh.strategy, current)
        fresh.apply_reflection("strategy", {"text": '```json\n{"parent": "top3"}\n```'})
        self.assertEqual(fresh.strategy["parent"], "top3")
        fresh._events.close()
        fresh._tsv.close()
        logged = _events(self.data.base / "evox-apply", "reflection")
        self.assertIn("strategy_error", logged[0])
        self.assertEqual(logged[1]["strategy"]["parent"], "top3")


class DescentFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()
        cls.result = evaluator.evaluate(POTENTIAL, split="train")

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def test_detail_matches_definition(self):
        detail = descent_detail(self.result, POTENTIAL)
        self.assertIsNotNone(detail)
        self.assertGreater(detail["no_descent"], 0)
        self.assertEqual(
            sum(detail["no_descent_classes"].values()), detail["no_descent"]
        )
        graph = next(g for g in self.result["graphs"] if g["graph"] == detail["graph"])
        self.assertTrue(graph["feedback"])
        table = evaluator.get_table(graph["m"], graph["r"])
        for ex in detail["examples"]:
            self.assertEqual(table.distance(tuple(ex["v"])), ex["d"])
            nb = ex["neighbours"]
            self.assertTrue(all(x["phi"] > ex["phi"] - 1 for x in nb.values()))
            self.assertTrue(any(x["d"] == ex["d"] - 1 for x in nb.values()))

    def test_compress_includes_detail_only_for_potential_spec(self):
        self.assertNotIn("descent_detail", compress(self.result))
        fb = compress(self.result, spec=POTENTIAL)
        self.assertIn("descent_detail", fb)
        self.assertLessEqual(len(json.dumps(fb)), MAX_BYTES)
        good = {"kind": "rules", "rules": [{"if": 1, "do": "L"}], "default": "L"}
        self.assertIsNone(descent_detail(self.result, good))


if __name__ == "__main__":
    unittest.main()
