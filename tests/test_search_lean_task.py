"""Track 3 (Lean in the loop): contract, bans, packets, scoring, sandbox profile, engine wiring.

Mock tests need no Lean. Integration tests run only when the pinned toolchain
(leanprover/lean4:v4.34.0) and the built lrxlean project are present.
"""
from argparse import Namespace
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest

from integrations import lean_task as T
from integrations import lean_worker as W

REFERENCE = T.TRACK_DIR / "reference" / "control-L1.lean"


class ContractTests(unittest.TestCase):
    def test_extract_last_lean_block_and_reject_truncation(self):
        text = "prose\n```lean\ntheorem a : True := trivial\n```\nmore\n```lean\ntheorem b : True := trivial\n```\n"
        self.assertIn("theorem b", T.extract_body(text))
        with self.assertRaises(ValueError):
            T.extract_body(text, "length")
        with self.assertRaises(ValueError):
            T.extract_body("no fence at all")
        with self.assertRaises(ValueError):
            T.extract_body("```lean\n" + "x" * (T.MAX_BODY_BYTES + 1) + "\n```")

    def test_bans_hit_exploits_and_spare_the_seed_and_control(self):
        cases = {"axiom f : False": "axiom", "theorem t : True := by native_decide": "native_decide",
                 "#eval 1": "# command", "set_option debug.skipKernelTC true": "set_option",
                 "open Lean in": "open Lean/IO/System/Std", "def f := IO.println 1": "Lean./IO./System./Std. identifier",
                 "import Mathlib": "import", "by decide +native": "+native", "_root_.LRX.x": "_root_",
                 "end Cand": "end", "unsafe def f": "unsafe", "@[init g] def f": "@[init",
                 "macro \"x\" : term => `(1)": "macro", "partial def f": "partial"}
        for text, rule in cases.items():
            self.assertIn(rule, T.lexical_violations(text), text)
        self.assertEqual(T.lexical_violations(T.seed_body()), [])
        if REFERENCE.is_file():
            self.assertEqual(T.lexical_violations(REFERENCE.read_text()), [])
        self.assertEqual(T.lexical_violations("def xs := #[1, 2]\ntheorem lend_x : True := trivial"), [])

    def test_sorry_policy_is_configurable(self):
        self.assertEqual(T.lexical_violations("theorem a : True := by sorry"), [])
        self.assertEqual(T.lexical_violations("theorem a : True := by sorry", forbid_sorry=True), ["sorry"])
        self.assertEqual(T.lexical_violations("axiom a : False", disabled=("axiom",)), [])

    def test_blocks_and_blanking_preserve_lines(self):
        body = "/-- doc\n more -/\n@[simp]\ntheorem a : True := trivial\n-- c\ntheorem L1 : Stmt.L1 := by\n  sorry\n"
        bl = T.blocks(body)
        self.assertEqual([(b["start"], b["name"]) for b in bl], [(1, "a"), (6, "L1")])
        self.assertEqual(T.declared_ids(body), ["L1"])
        blanked = T.blank_blocks(body, {1})
        self.assertEqual(blanked.count("\n"), body.count("\n"))
        self.assertNotIn("theorem a", blanked)
        self.assertIn("theorem L1", blanked)

    def test_footer_lines_and_forged_messages(self):
        body = "theorem L1 : Stmt.L1 := by\n  sorry\n"
        text, footer = T.assemble(body)
        lines = text.split("\n")
        for line, ident in footer.items():
            self.assertEqual(lines[line - 1], f"#print axioms Cand.{ident}")
        (line, ident), = footer.items()
        msgs = [json.dumps({"severity": "information", "pos": {"line": T.HEADER_LINES + 2, "column": 0},
                            "data": "'Cand.L1' does not depend on any axioms"}),
                json.dumps({"severity": "information", "pos": {"line": line, "column": 0},
                            "data": "'Cand.L1' depends on axioms: [propext, sorryAx]"})]
        out = T.parse_messages(msgs, footer, 3)
        self.assertEqual(out["printed_axioms"], {"L1": ["propext", "sorryAx"]})
        self.assertEqual(len(out["messages"]), 1)  # the forged body message stays a body message
        wrong = [json.dumps({"severity": "information", "pos": {"line": line, "column": 0},
                             "data": "'Cand.L2' does not depend on any axioms"})]
        self.assertEqual(T.parse_messages(wrong, footer, 3)["printed_axioms"], {})

    def test_comment_words_are_not_banned_but_code_and_hidden_code_are(self):
        for text in ("-- p is a prefix of w", "-- the postfix step", "-- the initialize case",
                     "-- proof works in Lean.", "-- at the end we use sorry\ntheorem a : True := trivial",
                     "/- nested /- end -/ prefix -/ theorem a : True := trivial", "/-- a docstring: infix -/"):
            self.assertEqual(T.lexical_violations(text), [], text)
        self.assertEqual(T.lexical_violations("-- we avoid sorry", forbid_sorry=True), [])
        for text, rule in {"-- #eval 1": "# command", "-- ```": "``` fence", "theorem end_ : True := trivial\nend": "end",
                           "theorem t (prefix : Nat) : True := trivial": "prefix",
                           'def s := "/-"\naxiom c : False\ndef t := "-/"': "axiom",
                           "def c := '\"'\ndef s := \"--\" axiom x : False": "axiom",
                           "def n := «a--b» axiom x : False": "axiom"}.items():
            self.assertIn(rule, T.lexical_violations(text), text)
        # anything the comment scan cannot lex exactly falls back to the raw text
        for text in ('def s := s!"{"--"}" axiom x : False', 'def s := r"\\" -- " axiom x : False',
                     "/- unterminated end", 'def s := "open'):
            self.assertIsNone(T.strip_comments(text), text)
        self.assertIn("end", T.lexical_violations("/- unterminated end"))
        stripped = T.strip_comments("a -- x\n/- y\n z -/ b")
        self.assertEqual(stripped.count("\n"), 2)
        self.assertNotIn("x", stripped)

    def test_declared_ids_ignore_layout_and_comments(self):
        body = (" theorem M1 : Stmt.M1 := x\n/-- d -/ theorem L2 : x\ntheorem\n  M3 : y\n-- theorem M4\n"
                "theorem M5x : z\ntheorem «M6» : w\ndef Stmt.L3 : Prop := True\n")
        self.assertEqual(T.declared_ids(body), ["L2", "M1", "M3", "M6"])
        text, footer = T.assemble(body, ["M1", "M9"])
        self.assertEqual(sorted(footer.values()), ["M1", "M9"])

    def test_footer_line_errors_are_kept_out_of_body_messages(self):
        body = "theorem M1 : Stmt.M1 := by\n  sorry\n"
        text, footer = T.assemble(body, list(T.IDS))
        line = next(ln for ln, i in footer.items() if i == "L2")
        msgs = [json.dumps({"severity": "error", "pos": {"line": line, "column": 14},
                            "data": "Unknown constant `Cand.L2`"})]
        out = T.parse_messages(msgs, footer, 3)
        self.assertEqual(out["messages"], [])
        self.assertIn("L2", out["footer_errors"])

    def test_score_is_exact_and_one_target_outweighs_partial_credit(self):
        one = T.score({"L1": "closed"}, 0, 5)
        partial = T.score({i: "closed" for i in T.MILESTONES}, 10, 0)
        self.assertEqual(Fraction(one["combined_exact"]), Fraction(1, 3) - Fraction(1, 20))
        self.assertEqual(Fraction(partial["combined_exact"]), Fraction(1, 5) + Fraction(1, 20))
        self.assertGreater(one["combined_score"], partial["combined_score"])
        self.assertEqual(T.score({}, 0, 0)["combined_score"], 0.0)

    def test_packet_is_capped_and_has_no_paths(self):
        from integrations.lean_evaluator import PACKET_MARK, instance_feedback, packet
        result = {"status": "VALID", "combined_score": 0.0, "T": "0", "M": "0", "P": "1/100", "aux": [],
                  "statuses": {i: "sorry" for i in T.IDS}, "axioms": {"L2": ["Cand.cheat"]},
                  "blocks": [{"start": 1, "end": 3, "name": "L1"}], "dropped_blocks": [],
                  "messages": [{"severity": "error", "line": 2, "col": 3,
                                "text": "unsolved goals /Users/someone/secret/file.lean " + "x" * 5000}] * 5}
        text = packet(result, "none")
        self.assertTrue(text.startswith(PACKET_MARK))
        self.assertLessEqual(len(text), 3000)
        self.assertNotIn("/Users", text)
        self.assertIn("Cand.cheat", text)
        self.assertIn("unsolved goals", instance_feedback(result, "L1"))
        self.assertNotIn("/Users", instance_feedback(result, "L1"))

    def test_lock_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "p"
            for name in T.LOCKED_FILES:
                (project / name).parent.mkdir(parents=True, exist_ok=True)
                (project / name).write_text(name)
            lock = Path(tmp) / "lean.lock.json"
            lock.write_text(json.dumps(T.compute_lock(project)))
            self.assertEqual(len(T.verify_lock(project, lock)), 64)
            (project / "LrxLean/Defs.lean").write_text("def Stmt.L1 : Prop := True")
            with self.assertRaisesRegex(RuntimeError, "Defs.lean"):
                T.verify_lock(project, lock)
            with self.assertRaises(RuntimeError):
                T.verify_lock(project, Path(tmp) / "missing.json")


class CacheKeyTests(unittest.TestCase):
    def _run(self, cache, *, sandbox=True, result=None):
        from unittest import mock
        from integrations import lean_evaluator as E
        result = result or {"status": "VALID", "combined_score": 0.0}
        with mock.patch.object(E, "check_toolchain", return_value="Lean (version 4.34.0, x)"), \
                mock.patch.object(E.T, "verify_lock", return_value="d" * 64), \
                mock.patch.object(E, "_evaluate_uncached", return_value=dict(result)) as uncached:
            out = E.evaluate("theorem a : True := trivial\n", cache_dir=cache, require_sandbox=sandbox)
        return out, uncached.call_count

    def test_key_binds_evaluator_source_and_sandbox(self):
        from unittest import mock
        from integrations import lean_evaluator as E
        args = ("body", {"x": 1}, "d" * 64, "v")
        base = E._cache_key(*args)
        self.assertNotEqual(base, E._cache_key(*args, False))
        with mock.patch.object(E, "evaluator_hash", return_value="0" * 64):
            self.assertNotEqual(base, E._cache_key(*args))

    def test_unsandboxed_and_no_verdict_results_are_never_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(tmp, sandbox=False)
            self.assertEqual(list(Path(tmp).iterdir()), [])
            self._run(tmp, result={"status": "INVALID", "combined_score": -1.0, "no_cache": True})
            self.assertEqual(list(Path(tmp).iterdir()), [])
            first, calls1 = self._run(tmp)
            second, calls2 = self._run(tmp)
            self.assertEqual((calls1, calls2, first["cache_hit"], second["cache_hit"]), (1, 0, False, True))
            _, calls3 = self._run(tmp, sandbox=False)  # an unsandboxed run never reads the cache
            self.assertEqual(calls3, 1)


@unittest.skipUnless(sys.platform == "darwin", "Seatbelt is macOS only")
class WorkerTests(unittest.TestCase):
    def test_profile_denies_network_and_generic_process_grants(self):
        text = W.lean_profile(exec_paths=["/bin/echo"], read_paths=["/tmp"], write_paths=[tempfile.gettempdir()])
        self.assertIn("(deny default)", text)
        for forbidden in ("(allow process*)", "network", "mach-lookup", "process-fork"):
            self.assertNotIn(forbidden, text)
        self.assertIn("(allow process-fork)", W.lean_profile(exec_paths=["/bin/echo"], allow_fork=True))

    def test_timeout_is_incomplete_and_sandbox_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = W.run(["/bin/sleep", "5"], cwd=tmp, env={"PATH": "/bin"}, wall=0.5, require_sandbox=False)
            self.assertEqual(out["status"], "INCOMPLETE")
            self.assertLess(out["seconds"], 4)
            with self.assertRaises(Exception):
                W.run(["/bin/echo"], cwd=tmp, env={}, require_sandbox=True)


class EngineWiringTests(unittest.TestCase):
    def test_engines_exclude_evox_and_sky_config_is_pinned(self):
        from integrations import lean_backends as B
        self.assertNotIn("evox", B.ENGINES)
        with tempfile.TemporaryDirectory() as tmp:
            args = Namespace(iterations=3, model="m", broker_url="http://127.0.0.1:1/v1", max_tokens=100,
                             llm_timeout=10, reasoning_effort=None, engine="adaevolve", eval_timeout=10,
                             evox_switch_interval=4, offline_no_auto_variation=True)
            cfg = json.loads(B._sky_config(args, Path(tmp)).read_text())
        self.assertEqual(cfg["language"], "lean")
        self.assertFalse(cfg["diff_based_generation"])
        self.assertFalse(cfg["evaluator"]["cascade_evaluation"])
        self.assertFalse(cfg["evaluator"]["inject_evaluator_context"])
        self.assertEqual(cfg["search"]["num_context_programs"], 1)
        self.assertEqual(cfg["search"]["database"]["random_seed"], B.RANDOM_SEED)
        self.assertEqual(cfg["prompt"]["system_message"], B.SYSTEM)

    def test_gepa_preflight_needs_one_fence_and_bans_apply(self):
        from integrations import lean_backends as B
        good = "```lean\ntheorem L1 : Stmt.L1 := by\n  sorry\n```"
        B.LeanBrokerLM._preflight(good, "stop")
        with self.assertRaises(ValueError):
            B.LeanBrokerLM._preflight(good + "\n```lean\ntheorem x : True := trivial\n```", "stop")
        with self.assertRaises(ValueError):
            B.preflight_source("```lean\naxiom f : False\n```")
        self.assertIn("theorem L1", B.preflight_source("Here it is.\n" + good))

    def test_research_status(self):
        from integrations.lean_backends import _research_status
        seed = {"closed_targets": [], "closed_milestones": []}
        self.assertEqual(_research_status(seed, {"closed_targets": ["L1"], "closed_milestones": []}, ["h"]),
                         "TARGET_CLOSED")
        self.assertEqual(_research_status(seed, {"closed_targets": [], "closed_milestones": ["M1"]}, ["h"]),
                         "MILESTONE_PROGRESS")
        self.assertEqual(_research_status(seed, seed, []), "NO_VALID_PROPOSAL")


@unittest.skipUnless(T.toolchain_available() and T.LOCK_PATH.is_file(), "pinned Lean toolchain not installed")
class LeanIntegrationTests(unittest.TestCase):
    def evaluate(self, body, **cfg):
        from integrations.lean_evaluator import evaluate
        return evaluate(body, config=cfg)

    def test_reference_L1_closes_and_stub_scores_zero(self):
        ref = self.evaluate(REFERENCE.read_text())
        self.assertEqual(ref["status"], "VALID")
        self.assertEqual(ref["closed_targets"], ["L1"])
        self.assertEqual(ref["footer_axioms"]["L1"], ["propext", "Quot.sound"])
        self.assertEqual(Fraction(ref["combined_exact"]), Fraction(1, 3) + Fraction(1, 20) * Fraction(8, 10))
        stub = self.evaluate(T.seed_body())
        self.assertEqual(stub["combined_score"], 0.0)
        self.assertEqual(set(stub["statuses"].values()), {"sorry"})

    def test_exploits_earn_nothing(self):
        body = (T.TRACK_DIR / "adversarial" / "exploits.lean").read_text()
        self.assertEqual(self.evaluate(body)["status"], "INVALID")
        res = self.evaluate(body, disabled_bans=["axiom", "native_decide"])
        self.assertEqual(res["combined_score"], 0.0)
        self.assertEqual(res["statuses"]["L1"], "wrong_type")
        self.assertEqual(res["statuses"]["L2"], "bad_axioms")
        self.assertEqual(res["statuses"]["L3"], "wrong_type")
        self.assertEqual(res["statuses"]["M1"], "wrong_type")
        self.assertEqual(res["statuses"]["M2"], "bad_axioms")
        self.assertEqual(res["statuses"]["M4"], "sorry")
        self.assertEqual(res["aux"], [])

    def test_lemma_spam_earns_no_helper_credit(self):
        lemmas = "".join(f"theorem t{k} : {k} = {k} := rfl\n" for k in range(1, 11))
        uses = "".join(f"  have := t{k}\n" for k in range(1, 11))
        res = self.evaluate(lemmas + "theorem L1 : Stmt.L1 := by\n" + uses + "  sorry\n")
        self.assertEqual((res["status"], res["A"], res["aux"], res["combined_score"]), ("VALID", "0", [], 0.0))
        res = self.evaluate(lemmas + "theorem M1 : Stmt.M1 := by\n" + uses
                            + "  intro p s v\n  simp only [exec, List.foldl_append]\n")
        self.assertEqual((res["closed_milestones"], res["aux"], res["A"]), (["M1"], [], "0"))

    def test_correct_proof_closes_in_any_layout(self):
        m1 = "theorem M1 : Stmt.M1 := by\n  intro p s v\n  simp only [exec, List.foldl_append]\n"
        for body in (" " + m1, "/-- doc -/ " + m1, m1.replace("theorem M1", "theorem\n  M1", 1),
                     "-- at the end, p is a prefix; this works in Lean.\n" + m1):
            res = self.evaluate(body)
            self.assertEqual((res["status"], res["closed_milestones"]), ("VALID", ["M1"]), body)
            self.assertEqual(res["footer_axioms"]["M1"], ["propext", "Quot.sound"])
        res = self.evaluate(" theorem M1 : Stmt.M1 := by\n  exact no_such_lemma\n")
        self.assertEqual(res["statuses"]["M1"], "error")

    def test_failing_block_is_pruned_and_rest_is_credited(self):
        body = ("theorem broken (v : List Nat) : rotL v = v := by\n  simp [rotL]\n\n"
                "theorem M1 : Stmt.M1 := by\n  intro p s v\n  simp only [exec, List.foldl_append]\n")
        res = self.evaluate(body)
        self.assertEqual(res["closed_milestones"], ["M1"])
        self.assertEqual([b["name"] for b in res["dropped_blocks"]], ["broken"])
        self.assertEqual(res["P"], "1/100")
        self.assertEqual(len(res["passes"]), 2)


if __name__ == "__main__":
    unittest.main()
