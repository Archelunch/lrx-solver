import contextlib
import io
import json
import unittest
from unittest.mock import patch

from src.lrx.cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main(list(args))
        return code, json.loads(output.getvalue() or errors.getvalue())

    def test_family_and_smoke(self):
        code, result = self.run_cli("family", "3")
        self.assertEqual(code, 0)
        self.assertEqual([c["projection"] for c in result["marks"]], [12, 12])
        self.assertEqual(self.run_cli("smoke")[0], 0)

    def test_actual_visible_bfs(self):
        code, result = self.run_cli("bfs", "2", "2")
        self.assertEqual(code, 0)
        self.assertEqual(result["states_discovered"], 12)
        code, result = self.run_cli("bfs", "3", "2", "--max-vertices", "5")
        self.assertEqual(code, 2)
        self.assertIsNone(result["sorting_radius"])

    def test_large_dp_refused_before_enumeration(self):
        code, result = self.run_cli("projection", "8", "2", "--q", "36")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_count_information(self):
        _, result = self.run_cli("info", "8", "2")
        self.assertEqual(result["counts"]["visible"], 1814400)
        self.assertEqual(result["counts"]["marked"], 3628800)

    def test_wrong_word_and_illegal_input_are_not_success(self):
        code, _ = self.run_cli(
            "verify", "2", "2", "", "--start", "2,1,0,0", "--mark", "2"
        )
        self.assertEqual(code, 1)
        code, _ = self.run_cli(
            "verify", "2", "2", "X", "--start", "2,1,0,0", "--mark", "0"
        )
        self.assertEqual(code, 2)
        code, result = self.run_cli(
            "verify", "2", "2", "X", "--start", "2,1,0,0", "--mark", "2"
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["terminal"])

    def test_projection_complete_even_when_bound_fails(self):
        code, result = self.run_cli("projection", "2", "2", "--q", "0")
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["covered"], 12)
        self.assertGreater(result["no_admissible_lift"], 0)
        self.assertFalse(result["conjecture_domain"])

    def test_live_cli_requires_opt_in(self):
        with patch("urllib.request.build_opener") as network:
            code, result = self.run_cli("experiment", "2", "1", "--provider", "xai")
            self.assertEqual(code, 2)
            self.assertIn("allow-network", result["reason"])
            network.assert_not_called()

    @patch.dict("os.environ", {"XAI_API_KEY": "test-only-key"})
    @patch("urllib.request.build_opener")
    def test_mocked_live_cli_integration(self, build):
        from tests.test_provider_adapter import (
            _good_api_response,
            _mock_opener,
            _mock_response,
        )

        build.return_value = _mock_opener(_mock_response(_good_api_response()))
        code, result = self.run_cli(
            "experiment",
            "2",
            "1",
            "--provider",
            "xai",
            "--allow-network",
            "--max-spend",
            "1",
            "--input-price",
            "1",
            "--output-price",
            "2",
            "--samples",
            "1",
            "--proposals",
            "1",
            "--max-requests",
            "1",
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["model_usage"]["requests"], 1)
        self.assertEqual(result["model_usage"]["model"], "grok-4.7")
        self.assertNotIn("test-only-key", json.dumps(result))
