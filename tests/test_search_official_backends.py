"""Trust and upstream-routing gates for executable official optimizers."""

import json
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from integrations import official_backends as official
from integrations.research_archive import DevelopmentArchive


FROZEN = (Path(__file__).resolve().parents[1] / "autoresearch" /
          "official-integration-260924" / "frozen")


class OfficialBackendTests(unittest.TestCase):
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
            self.assertIn("--- parent", payload)

    def test_reasoning_effort_reaches_both_official_request_paths(self):
        captured = {}

        def respond(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return io.BytesIO(b'{"choices":[{"message":{"content":"proposal"}}]}')

        lm = official.BrokerLM("http://127.0.0.1:8877/v1", "grok-4.7", 4096,
                               None, 600, "low")
        with patch.object(official, "urlopen", side_effect=respond):
            self.assertEqual(lm("Improve the program"), "proposal")
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
