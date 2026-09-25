"""Regressions for the loop-v3 review findings (sort_loop3.py, sort_loop3_finalize.py). Offline only."""
import json
from pathlib import Path
import tempfile
import unittest

from integrations import official_backends as ob
from integrations import sort_control_naive as naive
from integrations import sort_loop3 as L
from integrations import sort_loop3_finalize as F
from tests.test_search_loop_v3 import NAIVE, SWEEP, VENV, Server, chat, scored, tables42, venv_json
from tests.test_search_sort_task import small_states, write_set

EMPTY = "def sort_word(v):\n    return ''\n"  # test-authored seed: NOT_SORTED everywhere


def verifier(d, states, groups, minibatch):
    ids = [s["id"] for s in states]
    size = len(ids) // groups
    inst = {f"i{k}": ids[k * size:(k + 1) * size] for k in range(groups)}
    return L.SortVerifierV3(write_set(d, states), Path(d) / "run", cache_dir=Path(d) / "cache", engine="gepa",
                            instances=inst, screen_ids=ids[:3], budgets={}, reveal_cap=100, jobs=2,
                            require_os_sandbox=False, tables=tables42(), reveal_minibatch=minibatch)


class CoverageFullRowTest(unittest.TestCase):
    """Finding 1: a child evaluated as minibatch + valset remainder must get a full row."""

    def test_union_of_requests_appends_one_full_row(self):
        states, _ = small_states(12)
        with tempfile.TemporaryDirectory() as d:
            v = verifier(d, states, 3, 1)
            seed = v.evaluate(SWEEP.read_text(), "full", final=True, use_cache=False)
            v.evaluate_instances(SWEEP.read_text(), ["i0", "i1", "i2"])  # GEPA's seed valset request
            v.evaluate_instances(NAIVE.read_text(), ["i0"])  # child minibatch
            out = v.evaluate_instances(NAIVE.read_text(), ["i1", "i2"])  # valset remainder (cached i0 not resent)
            self.assertEqual(out["scope"], "full")
            self.assertIn("full", out)
            child_full = v.evaluate(NAIVE.read_text(), "full", final=True)
            rows = [r for r in v.state["evaluations"] if r["candidate_hash"] == child_full["candidate_hash"]]
            self.assertEqual([r["scope"] for r in rows], ["instances", "full", "full"])
            self.assertEqual(rows[1]["request_instances"], ["i1", "i2"])
            self.assertAlmostEqual(rows[1]["combined_score"], child_full["combined_score"])
            v.evaluate_instances(NAIVE.read_text(), ["i0"])  # later parent re-evaluation adds no full row
            self.assertEqual(sum(r["scope"] == "full" and r["candidate_hash"] == child_full["candidate_hash"]
                                 for r in v.state["evaluations"]), 2)
            self.assertNotEqual(seed["combined_score"], child_full["combined_score"])
            best = v.best_full()
            better = max((seed, child_full), key=lambda r: r["combined_score"])
            self.assertEqual(best["candidate_hash"], better["candidate_hash"])

    @unittest.skipUnless(VENV.exists(), "needs .venv-official")
    def test_real_gepa_picks_the_improved_child(self):
        """The pinned GEPA through the real _gepa_worker_v3 and HTTP verifier; LM stub proposes a better program."""
        script = r'''
import argparse, json, sys, tempfile
from pathlib import Path
from integrations import sort_control_naive as naive
from integrations import sort_loop3 as L
from tests.test_search_loop_v3 import CAMP, NAIVE, Server, chat, configs, tables42
from tests.test_search_sort_task import small_states, write_set
p = json.load(sys.stdin)
cc, bc, rbc = configs()
out = {}
for cache in (False, True):
    d = Path(tempfile.mkdtemp())
    states, _ = small_states(12)
    ids = [s["id"] for s in states]
    inst = {f"i{k}": ids[2 * k:2 * k + 2] for k in range(6)}
    knobs = L.engine_knobs(cc, "gepa", 1, bc, rbc)
    knobs["engine"].update(max_candidate_proposals=2, max_metric_calls=L.gepa_metric_calls(6, 3, 2))
    if cache:  # the pre-fix knob: GEPA sends only the uncached valset remainder for an accepted child
        knobs["engine"].update(cache_evaluation=True, cache_evaluation_storage="memory")
    v = L.SortVerifierV3(write_set(d, states), d / "run", cache_dir=d / "cache", engine="gepa", instances=inst,
                         screen_ids=ids[:3], budgets=knobs["verifier"], reveal_cap=100, jobs=2,
                         require_os_sandbox=False, tables=tables42(),
                         reveal_minibatch=knobs["reflection"]["reflection_minibatch_size"])
    v.evaluate(p["seed"], "full", final=True, use_cache=False)
    srv, url = v.serve()
    lm = Server(lambda path, body: chat("```python\n" + NAIVE.read_text() + "```"))
    (d / "seed.py").write_text(p["seed"])
    (d / "knobs.json").write_text(json.dumps(knobs))
    (d / "dataset.json").write_text(json.dumps({"instances": sorted(inst)}))
    (d / "out").mkdir()
    args = argparse.Namespace(seed=d / "seed.py", dataset=d / "dataset.json", knobs=d / "knobs.json",
                              run_dir=d / "out", broker_url=lm.url, verifier_url=url, model="flash", max_tokens=100,
                              llm_timeout=30, eval_timeout=120, reasoning_effort=None,
                              expected_first_prompt_sha256=None, expected_diagnosis_sha256=None, reflection_url=None,
                              reflection_model=None, reflection_max_tokens=None, reflection_timeout=None,
                              reflection_effort=None, diagnosis_max_chars=4000)
    try:
        summary = L._gepa_worker_v3(args)
    finally:
        srv.shutdown(); srv.server_close(); lm.close()
    reqs = []
    for f in sorted((d / "run" / "verified" / "evaluations").glob("result-*.json")):
        s = json.loads(f.read_text())["summary"]
        if "results" in s:
            reqs.append({"hash": s["candidate_hash"], "n": len(s["instances"]), "scope": s["scope"],
                         "optimal": sum(("optimal:" in r["side_info"]["feedback"]) for r in s["results"])})
    best = v.best_full()
    out[str(cache)] = {"requests": reqs, "best_hash": best["candidate_hash"], "best_score": best["combined_score"],
                       "gepa_best": summary["best_sha256"], "status": summary["status"],
                       "seed_score": v.seed["full"]["combined_score"], "revealed": list(v.reveal.ids),
                       "seed_hash": v.seed["full"]["candidate_hash"],
                       "full_rows": [(r["candidate_hash"], r["combined_score"]) for r in v.state["evaluations"]
                                     if r["scope"] == "full"]}
print(json.dumps(out))
'''
        got = venv_json(script, {"seed": EMPTY})
        for cache, g in got.items():
            with self.subTest(cache_evaluation=cache):
                self.assertEqual(g["status"], "COMPLETE")
                self.assertNotEqual(g["gepa_best"], g["seed_hash"])  # GEPA accepted the child
                self.assertEqual(g["best_hash"], g["gepa_best"])  # and the verifier's full-row argmax agrees
                self.assertGreater(g["best_score"], g["seed_score"])
                child = [r["n"] for r in g["requests"] if r["hash"] == g["gepa_best"]]
                self.assertEqual(child[:2], [3, 3] if cache == "True" else [3, 6])
        off = got["False"]
        # production knobs: seed valset, parent minibatch (re-evaluated), child minibatch, child valset
        self.assertEqual([(r["hash"] == off["seed_hash"], r["n"]) for r in off["requests"][:4]],
                         [(True, 6), (True, 3), (False, 3), (False, 6)])
        # optimal words appear only in the parent's re-evaluated minibatch, which is what reflection reads
        self.assertEqual([r["optimal"] > 0 for r in off["requests"][:4]], [False, True, False, False])
        self.assertTrue(off["revealed"])


class RevealPolicyTest(unittest.TestCase):
    """Finding 2: reveals are spent and recorded only for packets that can reach a proposer prompt."""

    def test_final_whole_child_and_remainder_packets_reveal_nothing(self):
        states, _ = small_states(12)
        with tempfile.TemporaryDirectory() as d:
            v = verifier(d, states, 3, 1)
            v.evaluate(EMPTY, "screen", final=True, use_cache=False)
            v.evaluate(EMPTY, "full", final=True, use_cache=False)
            self.assertEqual(v.reveal.ids, [])  # seed evaluations of the GEPA/Sky arms are never shown
            v.evaluate_instances(EMPTY, ["i0", "i1", "i2"])
            self.assertEqual(v.reveal.ids, [])  # valset request
            v.evaluate_instances(NAIVE.read_text(), ["i1"])
            v.evaluate_instances(NAIVE.read_text(), ["i0", "i2"])
            self.assertEqual(v.reveal.ids, [])  # child minibatch and valset remainder
            out = v.evaluate_instances(EMPTY, ["i1"])  # parent minibatch re-evaluation: reflection reads this
            self.assertIn("optimal:", out["results"][0]["side_info"]["feedback"])
            self.assertTrue(v.reveal.ids)
            self.assertTrue(set(v.reveal.ids) <= set(v.instances["i1"][k]["id"] for k in range(4)))
            n = len(v.reveal.ids)
            v.evaluate(EMPTY, "full", final=True)  # _finish_v3's final evaluation
            self.assertEqual(len(v.reveal.ids), n)

    def test_sequential_seed_packet_reveals_what_its_prompt_shows(self):
        states, _ = small_states(12)
        with tempfile.TemporaryDirectory() as d:
            ids = [s["id"] for s in states]
            v = L.SortVerifierV3(write_set(d, states), Path(d) / "run", cache_dir=None, engine="sequential",
                                 instances={"a": ids}, screen_ids=ids[:3], budgets={}, reveal_cap=100, jobs=2,
                                 require_os_sandbox=False, tables=tables42())
            out = v.evaluate(EMPTY, "full", final=True, use_cache=False, show=True)
            shown = [i for i in ids if f"- {i} " in out["packet"]]
            self.assertIn("optimal:", out["packet"])
            self.assertEqual(sorted(v.reveal.ids), sorted(shown))

    def test_blocks_dropped_by_the_size_cap_are_not_recorded(self):
        states, _ = small_states(12)
        res, rows = scored(states, lambda v: "")
        seed, _ = scored(states, naive.sort_word)
        reveal = L.Reveal(10)
        t = reveal.tentative()
        head, blocks = L.packet_parts(res, rows, "none", {s["id"]: s for s in states}, tables42(), seed, t, "full")
        self.assertEqual(len(t.granted), len(blocks))
        self.assertGreater(len(blocks), 1)
        text, kept = L.packet_text_n(head, blocks, len(head) + len(blocks[0]) + 1)
        self.assertEqual(kept, 1)
        t.commit(L.block_ids(rows, kept))
        self.assertEqual(reveal.ids, L.block_ids(rows, 1))
        self.assertIn(reveal.ids[0], text)
        art, kept2 = L.split_blocks_n(blocks, cap=max(len(b) for b in blocks[:2]) + 1)
        self.assertEqual(kept2, 2)  # one block per key
        full = L.Reveal(1).tentative()
        self.assertTrue(full.allow("x"))
        self.assertFalse(full.allow("y"))  # the cap counts pending grants


class LedgerStatsTest(unittest.TestCase):
    """Finding 3: finalize reads the ledgers _live_v3 writes."""

    def write(self, path, usd):
        path.write_text(json.dumps({"attempts": [{"charged_usd": usd}, {"charged_usd": 0.25}]}))

    def test_names_written_by_live_are_read(self):
        with tempfile.TemporaryDirectory() as d:
            flash, refl = L.ledger_paths(d, "gepa", 1)
            self.assertEqual((flash.name, refl.name),
                             ("broker-ledger-v3.gepa-s1.json", "broker-ledger-v3-reflection.gepa-s1.json"))
            self.write(flash, 1.5)
            self.write(refl, 2.0)
            got = F.ledger_stats(Path(d), "gepa", 1)
            self.assertEqual((got["flash_usd"], got["flash_calls"], got["reflection_usd"], got["reflection_calls"]),
                             (1.75, 2, 2.25, 2))
            m = {"ledger": str(flash), "reflection_ledger": None}  # manifest paths win; None = no reflection broker
            got = F.ledger_stats(Path(d), "gepa", 1, m)
            self.assertEqual((got["flash_usd"], got["reflection_usd"], got["reflection_calls"]), (1.75, 0, 0))
            missing = F.ledger_stats(Path(d), "gepa", 2)
            self.assertIsNone(missing["flash_usd"])
            self.assertIsNone(missing["reflection_calls"])

class DiagnosisFallbackTest(unittest.TestCase):
    """A truncated/invalid diagnosis (live 2026-09-25 sort-m9-v3-check: gemini-3.1-pro-preview truncated at
    max_tokens 3000, GEPA's own per-task retry burned the reflection sub-cap, BROKER_STOPPED on HTTP 429) must
    be retried once by ReflectThenWriteLM itself, then fall back to proposing without a diagnosis -- never
    reach GEPA's own retry, and never raise. A genuine broker halt (429/5xx) must still propagate immediately,
    uncaught and unretried, so BROKER_STOPPED still only means an actual broker halt."""

    def setUp(self):
        self.diag_calls, self.diag_finish = 0, "length"  # "length" == truncated every call, by default

        def diag(path, body):
            self.diag_calls += 1
            if self.diag_finish == 429:
                return 429, {"error": "stop"}
            return chat("A diagnosis.\n```python\nimport os\n```\nmore.", finish=self.diag_finish)

        def write(path, body):
            return chat("```python\ndef sort_word(v):\n    return ''\n```")
        self.d, self.w = Server(diag), Server(write)

    def tearDown(self):
        self.d.close()
        self.w.close()

    def lm(self):
        return L.make_lm(self.w.url, "flash", 100, 10, None, reflection_url=self.d.url, reflection_model="pro",
                         reflection_max_tokens=50, reflection_timeout=10)

    def test_truncated_diagnosis_retries_once_then_falls_back_without_raising(self):
        lm = self.lm()
        out = lm([{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])
        self.assertIn("def sort_word", out)  # the proposal still completes
        self.assertEqual(self.diag_calls, 2)  # one retry, not GEPA's own unbounded per-task retries
        sent = self.w.requests[0][1]["messages"]
        self.assertNotIn(L.DIAGNOSIS_APPEND, sent[-1]["content"])  # writer never saw a diagnosis
        receipt = lm.receipts[0]
        self.assertIsNone(receipt["diagnosis_sha256"])
        self.assertIsNotNone(receipt["diagnosis_fallback"])

    def test_diagnosis_recovers_on_the_retry(self):
        seq = iter(["length", "stop"])
        self.diag_finish = "length"

        def diag(path, body):
            self.diag_calls += 1
            return chat("A diagnosis.", finish=next(seq))
        self.d.close()
        self.d = Server(diag)
        lm = self.lm()
        out = lm([{"role": "user", "content": "U"}])
        self.assertIn("def sort_word", out)
        self.assertEqual(self.diag_calls, 2)
        sent = self.w.requests[0][1]["messages"]
        self.assertIn(L.DIAGNOSIS_APPEND, sent[-1]["content"])  # the second, successful diagnosis was used
        receipt = lm.receipts[0]
        self.assertIsNotNone(receipt["diagnosis_sha256"])  # recovered
        self.assertIsNotNone(receipt["diagnosis_fallback"])  # but the first attempt is still on record

    def test_genuine_broker_halt_is_not_retried_or_turned_into_a_fallback(self):
        self.diag_finish = 429
        lm = self.lm()
        with self.assertRaises(ob.BrokerHalted):
            lm([{"role": "user", "content": "U"}])
        self.assertEqual(self.diag_calls, 1)  # no retry burn on a genuine halt
        self.assertEqual(len(self.w.requests), 0)  # the writer (flash) was never called either

    def test_gepa_worker_records_fallback_counts_in_the_summary(self):
        with tempfile.TemporaryDirectory() as d:
            writer = L.SortBrokerLMv3(self.w.url, "flash", 100, None, 10, None)
            diag = L.DiagnosisLM(self.d.url, "pro", 50, None, 10, None)
            lm = L.ReflectThenWriteLM(diag, writer)
            lm([{"role": "user", "content": "U"}])
            lm([{"role": "user", "content": "V"}])
            self.assertEqual(self.diag_calls, 4)  # two proposals x (1 try + 1 retry) each
            self.assertEqual(sum(1 for r in lm.receipts if r["diagnosis_fallback"]), 2)
            self.assertEqual(sum(1 for r in lm.receipts if r["diagnosis_sha256"] is None), 2)


if __name__ == "__main__":
    unittest.main()
