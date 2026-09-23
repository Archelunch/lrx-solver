"""Tests for provider_adapter: BudgetLedger, XAIAdapter, OfflineMockProposer.

All HTTP calls are mocked; no live network activity occurs.
Tests cover: success, HTTP errors, URL errors, redirects, missing/invalid
usage, reservation charging on failure, token caps, and verifying the
API key does not appear in repr/str output.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from src.lrx.provider_adapter import (
    BudgetLedger,
    OfflineMockProposer,
    ProposalBudget,
    XAIAdapter,
    _build_prompt,
    _extract_json_object,
    _validate_https_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(body_dict, read_limit=None):
    """Build a mock response context manager returning body_dict as JSON bytes."""
    body = json.dumps(body_dict).encode()
    if read_limit is not None:
        body = body[:read_limit]
    mock_resp = MagicMock()
    mock_resp.read = MagicMock(return_value=body)
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_opener(response):
    op = MagicMock()
    op.open = MagicMock(return_value=response)
    return op


def _good_api_response(policy_json_str=None):
    if policy_json_str is None:
        policy_json_str = '{"weights": [3, 3, 2], "beam_width": 10, "max_steps": 200}'
    return {
        "choices": [{"message": {"content": policy_json_str}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 40},
    }


def _make_adapter(**kwargs):
    defaults = dict(
        base_url="https://api.x.ai/v1",
        model="grok-beta",
        allow_network=True,
        timeout_sec=5,
        max_requests=5,
        max_output_tokens=200,
        max_prompt_bytes=4096,
        max_response_bytes=32768,
    )
    defaults.update(kwargs)
    return XAIAdapter(**defaults)


def _make_ledger(**kwargs):
    defaults = dict(
        max_spend=1.0,
        input_cost_per_mtok=1.0,
        output_cost_per_mtok=2.0,
    )
    defaults.update(kwargs)
    return BudgetLedger(**defaults)


# ---------------------------------------------------------------------------
# BudgetLedger
# ---------------------------------------------------------------------------


class TestBudgetLedger(unittest.TestCase):
    def test_initial_state(self):
        ledger = _make_ledger()
        self.assertEqual(ledger.estimated_cost(), 0.0)
        self.assertEqual(ledger.requests_made, 0)

    def test_reserve_and_commit(self):
        ledger = _make_ledger(
            max_spend=1.0, input_cost_per_mtok=1.0, output_cost_per_mtok=1.0
        )
        self.assertTrue(ledger.reserve(500_000, 200_000))
        ledger.commit(actual_input_tokens=500_000, actual_output_tokens=200_000)
        # 0.5 + 0.2 = 0.7
        self.assertAlmostEqual(ledger.estimated_cost(), 0.7, places=6)
        self.assertEqual(ledger.requests_made, 1)

    def test_reserve_returns_false_when_over_budget(self):
        ledger = _make_ledger(max_spend=0.001)
        self.assertFalse(ledger.reserve(1_000_000, 1_000_000))
        # No request counted
        self.assertEqual(ledger.requests_made, 0)

    def test_charge_reservation_on_failure(self):
        ledger = _make_ledger(
            max_spend=1.0, input_cost_per_mtok=1.0, output_cost_per_mtok=1.0
        )
        reserved = ledger.reserve(500_000, 100_000)
        self.assertTrue(reserved)
        # Simulate failure — charge reservation
        ledger.charge_reservation()
        self.assertGreater(ledger.estimated_cost(), 0)
        self.assertEqual(ledger.requests_made, 1)

    def test_commit_invalid_negative_tokens_raises(self):
        ledger = _make_ledger()
        ledger.reserve(100, 100)
        with self.assertRaises(ValueError):
            ledger.commit(-1, 50)

    def test_commit_non_int_tokens_raises(self):
        ledger = _make_ledger()
        ledger.reserve(100, 100)
        with self.assertRaises(ValueError):
            ledger.commit(100.0, 50)  # float not allowed

    def test_reservation_clears_after_commit(self):
        ledger = _make_ledger(
            max_spend=1.0, input_cost_per_mtok=1.0, output_cost_per_mtok=1.0
        )
        ledger.reserve(100_000, 50_000)
        ledger.commit(100_000, 50_000)
        # Second reserve should succeed (reservation cleared)
        self.assertTrue(ledger.reserve(100_000, 50_000))

    def test_no_refund_after_charge_reservation(self):
        ledger = _make_ledger(
            max_spend=0.5, input_cost_per_mtok=1.0, output_cost_per_mtok=1.0
        )
        ledger.reserve(200_000, 200_000)  # reserves ~0.4
        ledger.charge_reservation()
        # Budget now mostly consumed; next large reserve should fail
        self.assertFalse(ledger.reserve(200_000, 200_000))

    def test_invalid_max_spend_raises(self):
        with self.assertRaises(ValueError):
            BudgetLedger(
                max_spend=-1.0, input_cost_per_mtok=1.0, output_cost_per_mtok=1.0
            )

    def test_invalid_rate_raises(self):
        with self.assertRaises(ValueError):
            BudgetLedger(
                max_spend=1.0, input_cost_per_mtok=0.0, output_cost_per_mtok=1.0
            )
        with self.assertRaises(ValueError):
            BudgetLedger(
                max_spend=1.0, input_cost_per_mtok=1.0, output_cost_per_mtok=-1.0
            )


# ---------------------------------------------------------------------------
# _validate_https_url
# ---------------------------------------------------------------------------


class TestValidateHttpsUrl(unittest.TestCase):
    def test_valid_url(self):
        _validate_https_url("https://api.x.ai/v1")  # must not raise

    def test_http_rejected(self):
        with self.assertRaises(ValueError):
            _validate_https_url("http://api.x.ai/v1")

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            _validate_https_url("https://user:pass@api.x.ai/v1")

    def test_query_rejected(self):
        with self.assertRaises(ValueError):
            _validate_https_url("https://api.x.ai/v1?key=secret")


# ---------------------------------------------------------------------------
# XAIAdapter construction and repr
# ---------------------------------------------------------------------------


class TestXAIAdapterConstruction(unittest.TestCase):
    def test_default_allow_network_is_false(self):
        adapter = XAIAdapter()
        self.assertFalse(adapter._allow_network)

    def test_http_url_raises(self):
        with self.assertRaises(ValueError):
            XAIAdapter(base_url="http://api.x.ai/v1")

    def test_repr_does_not_contain_api_key(self):
        adapter = _make_adapter()
        r = repr(adapter)
        # Even if XAI_API_KEY is set in env, repr must not include it
        import os

        key = os.environ.get("XAI_API_KEY", "secret-key-value")
        self.assertNotIn(key, r)
        self.assertNotIn("XAI_API_KEY", r)

    def test_str_does_not_contain_api_key(self):
        adapter = _make_adapter()
        s = str(adapter)
        import os

        key = os.environ.get("XAI_API_KEY", "secret-key-value")
        self.assertNotIn(key, s)

    def test_repr_shows_model_and_url(self):
        adapter = XAIAdapter(
            base_url="https://api.x.ai/v1",
            model="grok-beta",
            allow_network=True,
        )
        r = repr(adapter)
        self.assertIn("grok-beta", r)
        self.assertIn("api.x.ai", r)

    def test_attach_ledger_type_check(self):
        adapter = _make_adapter()
        with self.assertRaises(TypeError):
            adapter.attach_ledger("not-a-ledger")

    def test_propose_raises_when_network_disabled(self):
        adapter = XAIAdapter(allow_network=False)
        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)

    def test_propose_raises_without_ledger(self):
        adapter = _make_adapter(allow_network=True)
        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)


# ---------------------------------------------------------------------------
# XAIAdapter HTTP: success path
# ---------------------------------------------------------------------------


class TestXAIAdapterHTTPSuccess(unittest.TestCase):
    @patch.dict("os.environ", {"XAI_API_KEY": "test-key-abc"})
    @patch("urllib.request.build_opener")
    def test_successful_request_returns_policy(self, mock_build_opener):
        adapter = _make_adapter()
        ledger = _make_ledger(max_spend=1.0)
        adapter.attach_ledger(ledger)

        mock_build_opener.return_value = _mock_opener(
            _mock_response(_good_api_response())
        )

        policy = adapter.propose(2, 1)
        self.assertIn("weights", policy)
        self.assertIn("beam_width", policy)
        self.assertIn("max_steps", policy)

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_ledger_committed_on_success(self, mock_build_opener):
        adapter = _make_adapter()
        ledger = _make_ledger(max_spend=1.0)
        adapter.attach_ledger(ledger)

        mock_build_opener.return_value = _mock_opener(
            _mock_response(_good_api_response())
        )
        adapter.propose(2, 1)

        self.assertEqual(ledger.requests_made, 1)
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_api_key_not_in_request_repr(self, mock_build_opener):
        """Secret must not appear in any logged/printed data from adapter."""
        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        mock_build_opener.return_value = _mock_opener(
            _mock_response(_good_api_response())
        )
        adapter.propose(2, 1)
        # Key must not appear in repr/str
        self.assertNotIn("test-key", repr(adapter))
        self.assertNotIn("test-key", str(adapter))


# ---------------------------------------------------------------------------
# XAIAdapter HTTP: error paths
# ---------------------------------------------------------------------------


class TestXAIAdapterHTTPErrors(unittest.TestCase):
    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_http_error_charges_reservation(self, mock_build_opener):
        import urllib.error

        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError(
            url="https://api.x.ai/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )
        mock_build_opener.return_value = mock_opener

        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)

        # Reservation charged, not released
        self.assertEqual(ledger.requests_made, 1)
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_url_error_charges_reservation(self, mock_build_opener):
        import urllib.error

        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.URLError("Connection refused")
        mock_build_opener.return_value = mock_opener

        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)

        self.assertEqual(ledger.requests_made, 1)
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_raises(self):
        """XAI_API_KEY not set -> ValueError before any network call."""
        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        with self.assertRaises((RuntimeError, ValueError)):
            adapter.propose(2, 1)


# ---------------------------------------------------------------------------
# XAIAdapter: redirect rejection
# ---------------------------------------------------------------------------


class TestXAIAdapterRedirectRejection(unittest.TestCase):
    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_redirect_charges_reservation(self, mock_build_opener):
        import urllib.error

        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.URLError("Redirect 302 rejected")
        mock_build_opener.return_value = mock_opener

        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)

        # Reservation charged (not silently released)
        self.assertEqual(ledger.requests_made, 1)


# ---------------------------------------------------------------------------
# XAIAdapter: missing / invalid usage field
# ---------------------------------------------------------------------------


class TestXAIAdapterUsageValidation(unittest.TestCase):
    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_missing_usage_field_charges_reservation(self, mock_build_opener):
        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        # Response has no 'usage' key
        body = {
            "choices": [
                {
                    "message": {
                        "content": '{"weights":[3,3,2],"beam_width":10,"max_steps":200}'
                    }
                }
            ]
        }
        mock_build_opener.return_value = _mock_opener(_mock_response(body))

        with self.assertRaises(ValueError):
            adapter.propose(2, 1)

        # Reservation NOT released; it is charged
        self.assertEqual(ledger.requests_made, 1)
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_negative_usage_tokens_charges_reservation(self, mock_build_opener):
        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        body = {
            "choices": [
                {
                    "message": {
                        "content": '{"weights":[3,3,2],"beam_width":10,"max_steps":200}'
                    }
                }
            ],
            "usage": {"prompt_tokens": -5, "completion_tokens": 20},
        }
        mock_build_opener.return_value = _mock_opener(_mock_response(body))

        with self.assertRaises(ValueError):
            adapter.propose(2, 1)

        self.assertEqual(ledger.requests_made, 1)
        self.assertGreater(ledger.estimated_cost(), 0)

    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_float_usage_tokens_charges_reservation(self, mock_build_opener):
        adapter = _make_adapter()
        ledger = _make_ledger()
        adapter.attach_ledger(ledger)

        body = {
            "choices": [
                {
                    "message": {
                        "content": '{"weights":[3,3,2],"beam_width":10,"max_steps":200}'
                    }
                }
            ],
            "usage": {"prompt_tokens": 80.5, "completion_tokens": 40},
        }
        mock_build_opener.return_value = _mock_opener(_mock_response(body))

        with self.assertRaises(ValueError):
            adapter.propose(2, 1)

        self.assertEqual(ledger.requests_made, 1)


# ---------------------------------------------------------------------------
# XAIAdapter: request limit cap
# ---------------------------------------------------------------------------


class TestXAIAdapterRequestCap(unittest.TestCase):
    @patch.dict("os.environ", {"XAI_API_KEY": "test-key"})
    @patch("urllib.request.build_opener")
    def test_request_cap_enforced(self, mock_build_opener):
        adapter = _make_adapter(max_requests=1)
        ledger = _make_ledger(max_spend=100.0)
        adapter.attach_ledger(ledger)

        mock_build_opener.return_value = _mock_opener(
            _mock_response(_good_api_response())
        )

        adapter.propose(2, 1)  # first call succeeds

        with self.assertRaises(RuntimeError):
            adapter.propose(2, 1)  # second call should fail: limit reached


# ---------------------------------------------------------------------------
# _extract_json_object (no eval)
# ---------------------------------------------------------------------------


class TestExtractJsonObject(unittest.TestCase):
    def test_plain_json(self):
        text = '{"weights": [1, 2, 3], "beam_width": 5, "max_steps": 100}'
        obj = _extract_json_object(text)
        self.assertEqual(obj["weights"], [1, 2, 3])

    def test_embedded_in_text(self):
        text = 'Here is the policy: {"weights": [3, 3, 2], "beam_width": 10, "max_steps": 200} done.'
        obj = _extract_json_object(text)
        self.assertEqual(obj["beam_width"], 10)

    def test_no_object_raises(self):
        with self.assertRaises(ValueError):
            _extract_json_object("no braces here")

    def test_unterminated_raises(self):
        with self.assertRaises(ValueError):
            _extract_json_object('{"weights": [1, 2,')

    def test_no_eval_on_arbitrary_text(self):
        """Ensure we're using json.loads, not eval."""
        # This would be valid Python eval but not JSON
        text = '{"key": True}'  # Python True, not JSON
        with self.assertRaises(ValueError):
            _extract_json_object(text)


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt(unittest.TestCase):
    def test_contains_parameters(self):
        p = _build_prompt(2, 1)
        self.assertIn("m=2", p)
        self.assertIn("r=1", p)

    def test_does_not_contain_secrets(self):
        p = _build_prompt(3, 2)
        self.assertNotIn("Bearer", p)
        self.assertNotIn("API_KEY", p)

    def test_hint_included(self):
        p = _build_prompt(2, 1, hint="prefer X moves")
        self.assertIn("prefer X moves", p)


# ---------------------------------------------------------------------------
# OfflineMockProposer
# ---------------------------------------------------------------------------


class TestOfflineMockProposerProvider(unittest.TestCase):
    def test_words_contain_only_valid_letters(self):
        p = OfflineMockProposer(m=2, r=1, seed=0)
        for w in p.propose_words(count=10):
            self.assertTrue(all(c in "LRX" for c in w))

    def test_reproducible(self):
        w1 = OfflineMockProposer(m=2, r=1, seed=7).propose_words(5)
        w2 = OfflineMockProposer(m=2, r=1, seed=7).propose_words(5)
        self.assertEqual(w1, w2)

    def test_different_seeds_differ(self):
        w1 = OfflineMockProposer(m=2, r=1, seed=1).propose_words(3)
        w2 = OfflineMockProposer(m=2, r=1, seed=2).propose_words(3)
        self.assertNotEqual(w1, w2)


# ---------------------------------------------------------------------------
# ProposalBudget (compatibility)
# ---------------------------------------------------------------------------


class TestProposalBudgetProvider(unittest.TestCase):
    def test_offline_mode_cannot_afford(self):
        b = ProposalBudget(max_total_cost=None)
        self.assertFalse(b.can_afford_request(1000))

    def test_update_and_cost(self):
        b = ProposalBudget(
            max_total_cost=2.0,
            input_cost_per_mtok=1.0,
            output_cost_per_mtok=2.0,
        )
        b.update(1_000_000, 500_000)
        # 1.0 + 1.0 = 2.0
        self.assertAlmostEqual(b.estimated_cost(), 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
