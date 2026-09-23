import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.lrx import prompt
from src.lrx.evolve import Campaign, build_proposer, run_campaign
from src.lrx.llm import (
    BudgetExhausted,
    ChatClient,
    RequestAborted,
    SpendLedger,
    load_dotenv,
)
from src.lrx.proposers import LLMProposer, OfflineMutator
from tests.fixtures import TinyData

ROOT = Path(__file__).resolve().parents[1]
SEED = str(ROOT / "candidates/baselines/rules_bubble.json")


def _response(payload, stream=True):
    """Mock HTTP response. Streams the payload as server-sent events."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    lines = []
    if "choices" in payload:
        msg = payload["choices"][0].get("message") or {}
        if msg.get("reasoning_content"):
            lines.append(
                {
                    "choices": [
                        {"delta": {"reasoning_content": msg["reasoning_content"]}}
                    ]
                }
            )
        if "content" in msg:
            lines.append(
                {
                    "choices": [
                        {"delta": {"content": msg["content"]}, "finish_reason": "stop"}
                    ]
                }
            )
    if payload.get("usage"):
        lines.append({"choices": [], "usage": payload["usage"]})
    sse = [f"data: {json.dumps(x)}\n".encode() for x in lines] + [b"data: [DONE]\n"]
    resp.__iter__ = lambda s: iter(sse)
    resp.__enter__ = lambda s: s
    resp.__exit__ = lambda s, *a: False
    opener = MagicMock()
    opener.open.return_value = resp
    return opener


def _chat(text, tokens_in=100, tokens_out=50, reasoning=None):
    usage = {"prompt_tokens": tokens_in, "completion_tokens": tokens_out}
    if reasoning is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning}
    return {"choices": [{"message": {"content": text}}], "usage": usage}


class LedgerTests(unittest.TestCase):
    def test_limits_and_settle(self):
        ledger = SpendLedger(1.0, 1.0, 1.0, max_requests=2)
        r1 = ledger.reserve(100_000, 100_000)
        ledger.settle(r1, 1000, 1000)
        r2 = ledger.reserve(100_000, 100_000)
        ledger.settle(r2)  # failure: reservation charged
        self.assertAlmostEqual(ledger.committed, 0.002 + 0.2)
        with self.assertRaises(BudgetExhausted):
            ledger.reserve(1, 1)
        snap = ledger.snapshot()
        self.assertEqual((snap["requests"], snap["failed_requests"]), (2, 1))
        self.assertFalse(snap["billing_verified"])

    def test_spend_cap(self):
        ledger = SpendLedger(0.1, 1.0, 1.0, max_requests=100)
        with self.assertRaises(BudgetExhausted):
            ledger.reserve(100_000, 100_000)

    def test_concurrent_reservations_respect_cap(self):
        ledger = SpendLedger(1.0, 1.0, 1.0, max_requests=1000)
        ok = []

        def worker():
            try:
                ok.append(ledger.reserve(100_000, 100_000))
            except BudgetExhausted:
                pass

        threads = [threading.Thread(target=worker) for _ in range(20)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(ok), 5)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            SpendLedger(0, 1, 1, 1)
        with self.assertRaises(ValueError):
            SpendLedger(1, 1, 1, 0)


class ClientTests(unittest.TestCase):
    def client(self, **kw):
        return ChatClient(
            "https://api.example.com/v1",
            "grok-test",
            SpendLedger(1.0, 2.0, 6.0, 10),
            allow_network=True,
            **kw,
        )

    def test_network_disabled_by_default(self):
        client = ChatClient("https://api.example.com/v1", "m", SpendLedger(1, 1, 1, 1))
        with self.assertRaises(RuntimeError):
            client.complete([{"role": "user", "content": "hi"}])

    def test_http_url_rejected(self):
        with self.assertRaises(ValueError):
            ChatClient("http://api.example.com/v1", "m", SpendLedger(1, 1, 1, 1))

    @patch.dict(os.environ, {"XAI_API_KEY": "sk-test-secret"})
    @patch("urllib.request.build_opener")
    def test_success_counts_reasoning_tokens(self, opener):
        opener.return_value = _response(_chat("ok", 1000, 100, reasoning=900))
        client = self.client()
        out = client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(out["tokens_out"], 1000)
        self.assertAlmostEqual(out["cost_usd"], 1000 / 1e6 * 2 + 1000 / 1e6 * 6)
        request = opener.return_value.open.call_args[0][0]
        body = json.loads(request.data)
        self.assertEqual(body["model"], "grok-test")
        self.assertNotIn("sk-test-secret", repr(client))
        self.assertEqual(request.get_header("Authorization"), "Bearer sk-test-secret")

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_missing_usage_charges_reservation(self, opener):
        opener.return_value = _response({"choices": [{"message": {"content": "x"}}]})
        client = self.client()
        with self.assertRaises(ValueError):
            client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(client.ledger.failed, 1)
        self.assertGreater(client.ledger.committed, 0)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_provider_cost_and_reasoning_text(self, opener):
        payload = _chat("ok", 1000, 10, reasoning=200)
        payload["usage"]["cost_in_usd_ticks"] = 17_480_000
        payload["choices"][0]["message"]["reasoning_content"] = "thinking..."
        opener.return_value = _response(payload)
        out = self.client().complete([{"role": "user", "content": "hi"}])
        self.assertAlmostEqual(out["cost_usd"], 0.001748)
        self.assertEqual(out["cost_source"], "provider")
        self.assertEqual(out["reasoning"], "thinking...")
        self.assertEqual(out["reasoning_tokens"], 200)
        self.assertEqual(out["finish_reason"], "stop")
        sent = json.loads(opener.return_value.open.call_args[0][0].data)
        self.assertTrue(sent["stream"])

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_reasoning_budget_abort_charges_reservation(self, opener):
        payload = _chat("ok", 10, 10)
        payload["choices"][0]["message"]["reasoning_content"] = "x" * 400
        opener.return_value = _response(payload)
        client = self.client(max_reasoning_tokens=100)
        with self.assertRaises(RequestAborted):
            client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(client.ledger.failed, 1)
        self.assertGreater(client.ledger.committed, 0)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_wall_clock_cap(self, opener):
        opener.return_value = _response(_chat("ok"))
        client = self.client(timeout_sec=-1)
        with self.assertRaises(RequestAborted):
            client.complete([{"role": "user", "content": "hi"}])

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_non_stream_path(self, opener):
        opener.return_value = _response(_chat("plain", 5, 5))
        out = self.client(stream=False).complete([{"role": "user", "content": "hi"}])
        self.assertEqual(out["text"], "plain")
        sent = json.loads(opener.return_value.open.call_args[0][0].data)
        self.assertNotIn("stream", sent)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_network_error_names_cause(self, opener):
        import urllib.error

        opener.return_value.open.side_effect = urllib.error.URLError("timed out")
        with self.assertRaises(RuntimeError) as ctx:
            self.client().complete([{"role": "user", "content": "hi"}])
        self.assertIn("timed out", str(ctx.exception))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key(self):
        with self.assertRaises(ValueError):
            self.client().complete([{"role": "user", "content": "hi"}])

    def test_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("# c\nexport LRX_T_A='va'\nLRX_T_B=vb\nOTHER=1\nbad line\n")
            with patch.dict(os.environ, {"LRX_T_B": "keep"}, clear=False):
                names = load_dotenv(path, keys={"LRX_T_A", "LRX_T_B"})
                self.assertEqual(names, ["LRX_T_A"])
                self.assertEqual(os.environ["LRX_T_A"], "va")
                self.assertEqual(os.environ["LRX_T_B"], "keep")
                self.assertNotIn("OTHER", names)
                os.environ.pop("LRX_T_A")


class PromptTests(unittest.TestCase):
    def test_extract_candidate(self):
        text = 'idea\n```json\n{"kind":"bound","expr":1}\n```\nmore\n```json\n{"kind":"bound","expr":2}\n```'
        self.assertEqual(prompt.extract_candidate(text)["expr"], 2)
        self.assertEqual(prompt.extract_candidate('x {"a": 1} y'), {"a": 1})
        with self.assertRaises(ValueError):
            prompt.extract_candidate("no json")

    def test_prefix_stable_and_mentions_dsl(self):
        system = prompt.system_prompt(["rules"])
        self.assertEqual(prompt.prefix_hash(["rules"]), prompt.prefix_hash(["rules"]))
        self.assertIn("sum_tokens", system)
        self.assertIn('"kind":"rules"', system)
        self.assertNotIn('"kind":"potential"', system)
        self.assertLess(len(system) // 4, 3000)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_llm_proposer_parses_reply(self, opener):
        opener.return_value = _response(
            _chat('why\n```json\n{"kind":"bound","expr":"T"}\n```')
        )
        client = ChatClient(
            "https://api.example.com/v1",
            "m",
            SpendLedger(1, 1, 1, 5),
            allow_network=True,
        )
        out = LLMProposer(client).propose(
            "exploit",
            [({"kind": "bound", "expr": 1}, {})],
            ["bound"],
            "insight",
            seed=3,
        )
        self.assertEqual(out["spec"], {"kind": "bound", "expr": "T"})
        self.assertIsNone(out["error"])
        sent = json.loads(opener.return_value.open.call_args[0][0].data)
        self.assertIn("insight", sent["messages"][1]["content"])

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_repair_turn_fixes_invalid_candidate(self, opener):
        bad = _chat('```json\n{"kind":"bound","expr":["max_tokens","t","t"]}\n```')
        good = _chat('```json\n{"kind":"bound","expr":"T"}\n```')
        first, second_opener = _response(bad), _response(good)
        opener.side_effect = [first, second_opener]
        client = ChatClient(
            "https://api.example.com/v1",
            "m",
            SpendLedger(1, 1, 1, 5),
            allow_network=True,
        )
        out = LLMProposer(client, repairs=1).propose("exploit", [], ["bound"], seed=1)
        self.assertIsNone(out["error"])
        self.assertEqual(out["spec"], {"kind": "bound", "expr": "T"})
        self.assertEqual(out["repairs_used"], 1)
        self.assertIn("max_tokens takes 1 arguments", out["attempts"][0]["error"])
        sent = json.loads(second_opener.open.call_args[0][0].data)["messages"]
        self.assertEqual(sent[-2]["role"], "assistant")
        self.assertIn("validator rejected", sent[-1]["content"])
        self.assertEqual(client.ledger.requests, 2)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    @patch("urllib.request.build_opener")
    def test_repair_limit_and_kind_check(self, opener):
        wrong_kind = _chat('```json\n{"kind":"bound","expr":"T"}\n```')
        opener.side_effect = [_response(wrong_kind), _response(wrong_kind)]
        client = ChatClient(
            "https://api.example.com/v1",
            "m",
            SpendLedger(1, 1, 1, 5),
            allow_network=True,
        )
        out = LLMProposer(client, repairs=1).propose("exploit", [], ["rules"], seed=1)
        self.assertIn("not allowed", out["error"])
        self.assertEqual(len(out["attempts"]), 2)

    def test_live_provider_needs_flag(self):
        cfg = {
            "provider": {
                "type": "openai_compatible",
                "model": "m",
                "input_usd_per_mtok": 1,
                "output_usd_per_mtok": 1,
                "max_spend_usd": 1,
            }
        }
        with self.assertRaises(ValueError):
            build_proposer(cfg, allow_network=False)


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = TinyData().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.data.__exit__(None, None, None)

    def run_engine(self, engine):
        cfg = {
            "name": f"t-{engine}",
            "engine": engine,
            "kinds": ["rules"],
            "seeds": [SEED],
            "max_proposals": 6,
            "batch": 3,
            "eval_workers": 2,
            "islands": 2,
            "migration_every": 3,
            "stagnation": 3,
            "seed": 5,
        }
        run_dir = self.data.base / f"runs-{engine}"
        summary = run_campaign(cfg, run_dir)
        self.assertEqual(summary["proposals"], 6)
        self.assertEqual(summary["stop_reason"], "max_proposals")
        for name in (
            "config.json",
            "events.jsonl",
            "results.tsv",
            "summary.json",
            "best.json",
        ):
            self.assertTrue((run_dir / name).exists(), name)
        rows = (run_dir / "results.tsv").read_text().strip().splitlines()
        self.assertEqual(len(rows), 1 + 1 + 6)  # header + seed + proposals
        events = [
            json.loads(line)
            for line in (run_dir / "events.jsonl").read_text().splitlines()
        ]
        held = [e for e in events if e["event"] == "heldout"]
        self.assertTrue(held and all(e["feedback"] is False for e in held))
        for e in events:
            if e["event"] == "candidate":
                self.assertNotIn("m4r3", json.dumps(e["feedback"]))
        self.assertGreaterEqual(summary["best"]["score"], summary["seed_best"])
        with self.assertRaises(FileExistsError):
            run_campaign(cfg, run_dir)
        return events

    def test_engines(self):
        for engine in ("best_of_n", "sequential", "gepa", "adaevolve"):
            with self.subTest(engine=engine):
                events = self.run_engine(engine)
                if engine == "adaevolve":
                    self.assertTrue(any(e["event"] == "migration" for e in events))

    def test_unknown_key_and_disallowed_kind(self):
        with self.assertRaises(ValueError):
            Campaign({"bogus": 1}, self.data.base / "x1", OfflineMutator())
        campaign = Campaign(
            {"kinds": ["rules"]}, self.data.base / "x2", OfflineMutator()
        )
        res = campaign.evaluate_specs([{"kind": "bound", "expr": 1}], pool=None)
        self.assertFalse(res[0]["valid"])
        self.assertIn("not allowed", res[0]["error"])
        campaign._events.close()
        campaign._tsv.close()


class OfflineMutatorTests(unittest.TestCase):
    def test_deterministic_and_valid(self):
        from src.lrx.candidates import Candidate

        spec = json.loads(Path(SEED).read_text())
        a = OfflineMutator(1).propose("explore", [(spec, {})], ["rules"], seed=7)
        b = OfflineMutator(1).propose("explore", [(spec, {})], ["rules"], seed=7)
        self.assertEqual(a, b)
        Candidate(a["spec"])
        for kind_spec in (
            {"kind": "potential", "expr": "disp_sum"},
            {"kind": "radius", "expr": "n"},
            {"kind": "beam", "expr": "cinv", "beam_width": 4},
        ):
            for s in range(10):
                Candidate(
                    OfflineMutator(s).propose("exploit", [(kind_spec, {})], [], seed=s)[
                        "spec"
                    ]
                )


if __name__ == "__main__":
    unittest.main()


class PromptExampleTests(unittest.TestCase):
    def test_every_prompt_example_is_valid(self):
        from src.lrx.candidates import Candidate

        for kind, items in prompt.EXAMPLES.items():
            for text in items:
                self.assertEqual(Candidate(json.loads(text)).kind, kind)

    def test_json_error_is_specific(self):
        with self.assertRaises(ValueError) as ctx:
            prompt.extract_candidate('```json\n{"kind":"rules",,}\n```')
        self.assertIn("at char", str(ctx.exception))
