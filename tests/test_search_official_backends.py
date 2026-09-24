"""Trust and upstream-routing gates for executable official optimizers."""

import json
import io
from pathlib import Path
import tempfile
import types
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from integrations import official_backends as official
from integrations.research_archive import DevelopmentArchive


FROZEN = (Path(__file__).resolve().parents[1] / "autoresearch" /
          "official-integration-260924" / "frozen")


class OfficialBackendTests(unittest.TestCase):
    def test_hard_case_sampler_always_sees_open_case_and_rotates_regressions(self):
        class Loader:
            def all_ids(self):
                return list(range(6))
            def fetch(self, ids):
                return [{"id": ("hard" if i == 4 else f"solved-{i}")} for i in ids]

        sampler = official.HardCaseBatchSampler({"hard"})
        batches = [sampler.next_minibatch_ids(Loader(), types.SimpleNamespace(i=i))
                   for i in range(3)]
        self.assertEqual([batch[0] for batch in batches], [4, 4, 4])
        self.assertEqual(batches[0][1:], [0, 1])
        self.assertEqual(batches[1][1:], [2, 3])
        self.assertEqual(batches[2][1:], [5, 0])
        all_hard = official.HardCaseBatchSampler({f"hard-{i}" for i in range(4)})
        class FourHardLoader:
            def all_ids(self):
                return list(range(4))
            def fetch(self, ids):
                return [{"id": f"hard-{i}"} for i in ids]
        self.assertEqual(all_hard.next_minibatch_ids(FourHardLoader(), types.SimpleNamespace(i=0)),
                         [0, 1, 2, 3])

    def test_gepa_model_preflight_rejects_prose_syntax_and_truncation(self):
        valid = "```python\ndef propose_words(case):\n    return []\n```"
        official.BrokerLM._preflight(valid, "stop")
        for content, reason in (("I will try a new idea", "stop"),
                                ("```python\ndef propose_words(case):\n return [\n```", "stop"),
                                (valid, "length")):
            with self.subTest(content=content[:20], reason=reason), self.assertRaises((ValueError, SyntaxError)):
                official.BrokerLM._preflight(content, reason)

    def test_halted_broker_aborts_gepa_reflection_without_local_retry(self):
        lm = official.BrokerLM("http://127.0.0.1:8877/v1", "grok-4.7", 4096,
                               None, 10, "low")
        self.assertFalse(issubclass(official.BrokerHalted, Exception))
        for error in (HTTPError(lm.url, 502, "timeout", {}, None),
                      HTTPError(lm.url, 429, "halted", {}, None),
                      URLError("connection refused"), TimeoutError("read timeout")):
            with self.subTest(error=str(error)), patch.object(official, "urlopen", side_effect=error):
                with self.assertRaises(official.BrokerHalted):
                    lm("Improve the program")
        self.assertEqual(lm.calls, 4)
        self.assertEqual(lm.valid_responses, 0)

    def test_mechanism_evidence_does_not_count_bootstrap_as_strategy_rewrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            search = root / "output" / "sky" / "search" / "iteration_1"
            search.mkdir(parents=True)
            (search / "metadata.json").write_text('{"is_fallback":true}')
            (search / "code.py").write_text("class InitialSearch: pass\n")
            (root / "console.log").write_text("No valid diffs found in LLM response\n" * 3)
            evox = official._mechanism_evidence(root, "evox", 2)
            self.assertEqual(evox["generated_strategy_artifacts"], [])
            self.assertTrue(evox["fallback_strategy_records"])
            self.assertFalse(evox["strategy_adopted_confirmed"])
            self.assertEqual(evox["solution_diff_parse_failures"], 3)
            row = {"global": {"ucb_min_visits": 3}, "config": {"migration_interval": 15},
                   "islands": [{"ucb_raw_visits": 2}, {"ucb_raw_visits": 1}],
                   "paradigm": {"window_size": 10, "num_tried_paradigms": 0},
                   "iteration_result": {"success": True}}
            (root / "output" / "sky" / "adaevolve_iteration_stats_fixture.jsonl").write_text(
                json.dumps(row) + "\n")
            ada = official._mechanism_evidence(root, "adaevolve", 3)
            self.assertEqual(ada["ucb_island_visits"], [2, 1])
            self.assertFalse(ada["ucb_min_visits_reached"])
            self.assertFalse(ada["migration_opportunity"])
            self.assertEqual(ada["paradigms_tried"], 0)

    def test_frozen_development_pair_and_trusted_lock(self):
        args = types.SimpleNamespace(
            cases=FROZEN / "development.json",
            baseline=FROZEN / "development-baseline.json",
            frozen_manifest=None, allow_custom_cases=False)
        with patch("tools.orchestrator.trusted_status", return_value={"ok": True}):
            provenance = official._verify_inputs(args)
            self.assertEqual(provenance["frozen_manifest_sha256"],
                             official._source_digest(FROZEN / "manifest.json"))
        with patch("tools.orchestrator.trusted_status", return_value={"ok": False, "changed": ["x"]}):
            with self.assertRaisesRegex(RuntimeError, "trusted core lock mismatch"):
                official._verify_inputs(args)
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "development.json"
            bad.write_text(args.cases.read_text() + " ")
            args.cases = bad
            args.frozen_manifest = FROZEN / "manifest.json"
            with patch("tools.orchestrator.trusted_status", return_value={"ok": True}):
                with self.assertRaisesRegex(RuntimeError, "frozen hash mismatch"):
                    official._verify_inputs(args)

    def test_pinned_installed_identity(self):
        python = official.ROOT / ".venv-official" / "bin" / "python"
        if not python.exists():
            self.skipTest("official optional environment is not installed")
        self.assertEqual(official._installed_identity(python, "gepa"), "gepa==0.1.4")
        self.assertIn("0d932b690670", official._installed_identity(python, "evox"))

    def test_best_snapshot_rejects_path_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            output.mkdir()
            verified = root / "verified"
            best = output / "best.py"
            best.write_text("def propose_words(case): return []\n")
            snapshot = official._snapshot_best(best, output, verified)
            self.assertEqual(snapshot.read_bytes(), best.read_bytes())
            best.unlink()
            best.symlink_to(snapshot)
            with self.assertRaises(FileNotFoundError):
                official._snapshot_best(best, output, verified)
            with self.assertRaises(ValueError):
                official._snapshot_best(snapshot, output, verified)
            best.unlink()
            best.write_bytes(b"x" * 65537)
            with self.assertRaisesRegex(ValueError, "source cap"):
                official._snapshot_best(best, output, verified)

    def test_completion_requires_successful_candidate_replay(self):
        clean = {"families": [{"candidate_run": {"status": "ok"}}]}
        failed = {"families": [{"candidate_run": {"status": "INCOMPLETE"}}]}
        self.assertEqual(official._completion_status({"successes": 1}, clean), "COMPLETE")
        self.assertEqual(official._completion_status({"successes": 0}, clean), "INCOMPLETE")
        self.assertEqual(official._completion_status({"successes": 1}, failed), "INCOMPLETE")

    def test_research_status_accepts_exact_fractional_progress(self):
        manifest = {"status": "COMPLETE", "verified_new_vs_incumbent": 0,
                    "verified_secondary_score": "14887/630696",
                    "valid_proposal_hashes": ["candidate"]}
        self.assertEqual(official._research_status(manifest), "GRADED_PROGRESS")
        manifest["verified_secondary_score"] = "0"
        self.assertEqual(official._research_status(manifest), "NO_GAIN")

    def test_gepa_file_stopper_only_after_full_valid_incumbent_gain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = {"new_vs_incumbent": 1,
                      "families": [{"candidate_run": {"status": "ok"}}]}
            self.assertFalse(official._stop_gepa_after_new_certificate(result, "hard", root, "gepa"))
            self.assertFalse(official._stop_gepa_after_new_certificate(result, None, root, "evox"))
            self.assertFalse((root / "output" / "gepa" / "gepa.stop").exists())
            self.assertTrue(official._stop_gepa_after_new_certificate(result, None, root, "gepa"))
            self.assertTrue((root / "output" / "gepa" / "gepa.stop").is_file())

    def test_archive_context_contains_raw_traces_and_source_diff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = DevelopmentArchive(root / "archive.sqlite")
            try:
                row_id = archive.add(run_id="dev", engine="gepa", source="def propose_words(case):\n return []\n",
                                     score=0, feedback={"reason": "test"},
                                     traces=[{"raw": "TRACE_MARKER"}], provenance={"split": "development"})
            finally:
                archive.close()
            args = types.SimpleNamespace(archive=root / "archive.sqlite", archive_query="",
                                         archive_limit=1)
            context, ids = official._stage_archive(args, root)
            payload = context.read_text()
            self.assertEqual(ids, [row_id])
            self.assertIn("TRACE_MARKER", payload)
            self.assertNotIn("--- parent", payload)  # No parent was declared.

    def test_reasoning_effort_reaches_both_official_request_paths(self):
        captured = {}

        def respond(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return io.BytesIO(b'{"choices":[{"message":{"content":"```python\\ndef propose_words(case):\\n    return []\\n```"},"finish_reason":"stop"}]}')

        lm = official.BrokerLM("http://127.0.0.1:8877/v1", "grok-4.7", 4096,
                               None, 600, "low")
        with patch.object(official, "urlopen", side_effect=respond):
            self.assertIn("def propose_words", lm("Improve the program"))
        self.assertEqual(captured["payload"]["reasoning_effort"], "low")
        self.assertEqual(captured["payload"]["model"], "grok-4.7")
        self.assertEqual(captured["timeout"], 600)

        with tempfile.TemporaryDirectory() as temp:
            args = types.SimpleNamespace(
                engine="evox", iterations=2, sky_log_level="INFO", model="grok-4.7",
                broker_url="http://127.0.0.1:8877/v1", max_tokens=4096,
                llm_timeout=600, reasoning_effort="low", offline_no_auto_variation=False,
                evox_switch_interval=2, eval_timeout=120)
            config = json.loads(official._sky_config(args, Path(temp), None, None).read_text())
            self.assertEqual(config["llm"]["reasoning_effort"], "low")
            self.assertTrue(config["search"]["database"]["auto_generate_variation_operators"])

    def test_focused_gepa_steering_is_opt_in_and_keeps_research_prompt(self):
        captured = []

        def respond(request, timeout):
            captured.append(json.loads(request.data))
            return io.BytesIO(b'{"choices":[{"message":{"content":"```python\\ndef propose_words(case):\\n    return []\\n```"},"finish_reason":"stop"}]}')

        base = official.BrokerLM("http://127.0.0.1:8877/v1", "grok-4.7", 4096,
                                 None, 10, "low")
        focused = official.BrokerLM("http://127.0.0.1:8877/v1", "grok-4.7", 4096,
                                    None, 10, "low", focused_reflection=True)
        with patch.object(official, "urlopen", side_effect=respond):
            base("Native GEPA reflection prompt")
            focused("Native GEPA reflection prompt")
        self.assertEqual(captured[0]["messages"],
                         [{"role": "user", "content": "Native GEPA reflection prompt"}])
        self.assertEqual(captured[1]["messages"][0]["content"],
                         official.FOCUSED_GEPA_STEERING)
        self.assertEqual(captured[1]["messages"][1], captured[0]["messages"][0])

    def test_reviewed_archive_context_is_staged_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reviewed = root / "reviewed.json"
            reviewed.write_bytes(b'[{"id":1,"traces":[{"status":"NO_CERTIFICATE"}]}]\n')
            stage = root / "stage"
            stage.mkdir()
            args = types.SimpleNamespace(archive=None, archive_context_file=reviewed)
            staged, ids = official._stage_archive(args, stage)
            self.assertEqual(ids, [1])
            self.assertEqual(staged.read_bytes(), reviewed.read_bytes())


if __name__ == "__main__":
    unittest.main()
