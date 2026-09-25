"""Regression tests for autoresearch/TRACE-AUDIT-260925.md, offline only (no provider calls).

Each test targets one numbered defect from that audit and fails against the
pre-fix code.
"""
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from fractions import Fraction as Fr
from unittest.mock import patch

from integrations import corr_backends as CB
from integrations import lift_backends as LB
from integrations import official_backends as OB

ROOT = Path(__file__).resolve().parents[1]
CORR_DIR = ROOT / 'autoresearch' / 'corr-cert-260924'
LIFT_DIR = ROOT / 'autoresearch' / 'lift-m9-260924'


class Defect1FractionParsing(unittest.TestCase):
    """The SkyDiscover evaluator.py corr_backends generates must parse a rational
    violation_sum string via Fraction, never bare float()."""

    def test_generated_evaluator_uses_fraction_not_bare_float(self):
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            path = CB._sky_evaluator(stage, 'http://127.0.0.1:1/evaluate', 5)
            src = path.read_text()
        self.assertIn('from fractions import Fraction', src)
        self.assertIn("Fraction(out['violation_sum'])", src)
        self.assertNotIn("float(out['violation_sum'])", src)

    def test_rational_violation_sum_string_parses_correctly(self):
        # This is exactly the shape corr_evaluator.py emits (str(Fraction(...))).
        raw = '56934268/3465'
        with self.assertRaises(ValueError):
            float(raw)  # the bug: bare float() on a fraction string
        self.assertAlmostEqual(float(Fr(raw)), 56934268 / 3465)


class Defect2PerArmSubCaps(unittest.TestCase):
    def _configs(self, d, requests_by_engine):
        bc = {"ledger": "ledger.json", "max_requests": sum(requests_by_engine.values())}
        cc = {"engines": {name: {"max_requests": cap} for name, cap in requests_by_engine.items()}}
        return bc, cc

    def test_sub_cap_zero_is_refused(self):
        bc, cc = self._configs(Path('.'), {"gepa": 10, "evox": 0})
        sub_cap, remaining = CB.arm_contact_budget(bc, cc, "evox")
        self.assertEqual((sub_cap, remaining), (0, 10))

    def test_earlier_arms_cannot_drain_a_later_arms_share(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            bc = {"ledger": str(d / "ledger.json"), "max_requests": 10}
            cc = {"engines": {"gepa": {"max_requests": 6}, "evox": {"max_requests": 4}}}
            # gepa's arm-scoped ledger recorded 6 attempts (its own sub-cap, fully used)
            gepa_ledger = CB._arm_ledger_path(bc, "gepa")
            (d / gepa_ledger).write_text(json.dumps({"attempts": [{}] * 6}))
            sub_cap, remaining = CB.arm_contact_budget(bc, cc, "evox")
            # Before the fix, one shared ledger meant gepa's 6 calls could leave
            # evox with 10-6=4 only by accident of ordering, or (worse, as in
            # the live corr campaign) 0 if an earlier arm used the whole 10.
            self.assertEqual((sub_cap, remaining), (4, 4))
            gepa2_ledger = CB._arm_ledger_path(bc, "gepa")
            self.assertEqual(gepa2_ledger, gepa_ledger)

    def test_lift_and_corr_campaign_configs_declare_nonzero_sub_caps(self):
        for cc_path, bc_path in ((CORR_DIR / 'campaign-config.json', CORR_DIR / 'broker-config.json'),
                                 (LIFT_DIR / 'campaign-config.json', LIFT_DIR / 'broker-config.json')):
            cc = json.loads(cc_path.read_text())
            bc = json.loads(bc_path.read_text())
            for name in cc['engines']:
                self.assertIn('max_requests', cc['engines'][name])
                self.assertGreater(cc['engines'][name]['max_requests'], 0)
            self.assertLessEqual(sum(e['max_requests'] for e in cc['engines'].values()), bc['max_requests'])


class Defect3PreflightAcceptsProseAndLastFence(unittest.TestCase):
    def test_lift_multiple_fences_last_defining_wins(self):
        scratch = "```python\n# scratch, not a real answer\nx = 1\n```\n"
        real = "```python\ndef lift(instance):\n    return {'words': []}\n```"
        src = LB.preflight_source("Let me think.\n" + scratch + "\nHere's my answer:\n" + real, 'stop')
        self.assertIn('def lift', src)
        self.assertNotIn('scratch', src)

    def test_corr_multiple_fences_last_defining_wins(self):
        scratch = "```python\nm = 4  # scratch\n```\n"
        real = "```python\ndef coefficients(m):\n    return {}\n```"
        src = CB.preflight_source("prose\n" + scratch + "more prose\n" + real + "\ntrailing prose", 'stop')
        self.assertIn('def coefficients', src)

    def test_truncated_output_is_never_repaired(self):
        real = "```python\ndef lift(instance):\n    return {'words': []}\n```"
        with self.assertRaises(ValueError):
            LB.preflight_source(real, 'length')


class Defect4RejectionHistoryAndGuard(unittest.TestCase):
    def test_rejection_note_shows_last_three_most_recent_last(self):
        history = [{"step": i, "reason": f"r{i}"} for i in range(1, 6)]
        note = LB.rejection_note(history)
        self.assertNotIn('r1', note)
        self.assertNotIn('r2', note)
        for i in (3, 4, 5):
            self.assertIn(f'r{i}', note)
        self.assertLess(note.index('r3'), note.index('r4'))
        self.assertLess(note.index('r4'), note.index('r5'))

    def test_empty_history_gives_empty_note(self):
        self.assertEqual(LB.rejection_note([]), "")
        self.assertEqual(CB.rejection_note([]), "")

    def test_corr_rejection_note_matches_lift(self):
        history = [{"step": 1, "reason": "invalid proposal: bad"}]
        self.assertIn('bad', CB.rejection_note(history))


class Defect5ReflectionMinibatch(unittest.TestCase):
    def test_corr_single_example_dataset_uses_minibatch_one(self):
        train = [{"id": "development"}]
        self.assertEqual(CB.reflection_minibatch_size(train), 1)
        self.assertEqual(CB.gepa_metric_calls_per_proposal(1, train), 3)

    def test_lift_large_dataset_caps_at_three(self):
        train = [{"id": f"p{i}"} for i in range(210)]
        val = [{"id": f"s{i}"} for i in range(14)]
        self.assertEqual(LB.reflection_minibatch_size(train), 3)
        self.assertEqual(LB.gepa_metric_calls_per_proposal(3, val), 2 * 3 + 14)


class Defect7PacketBestSoFar(unittest.TestCase):
    """A fake evaluation archive (self.state['evaluations']) with only
    parent-scoped rows must still surface a best_full once one of those rows
    carries a full-development result (LiftVerifier._current_best)."""

    def test_parent_scoped_eval_with_full_result_sets_best_full(self):
        v = LB.LiftVerifier.__new__(LB.LiftVerifier)
        v.screen = [None] * 10
        v.full = [None] * 100
        v.state = {"evaluations": []}
        # A parent-scoped GEPA call with no full eval: must not move best_full.
        v.state["evaluations"].append({
            "scope": "parent p00", "candidate_hash": "h1", "combined_score": 1.0,
            "certificates": 1, "valid": 1, "instances": 1,
            "full_certificates": None, "full_combined_score": None,
            "full_valid": None, "full_instances": None, "full_gap_sum": None})
        best_screen, best_full = v._current_best()
        self.assertIsNone(best_full)
        self.assertEqual(v._best_text(best_screen, best_full), "none")
        # A parent-scoped *final* call that did run a full-development eval
        # (defect 7's fix: no longer gated to parent_id is None) must set it.
        v.state["evaluations"].append({
            "scope": "parent p01", "candidate_hash": "h2", "combined_score": 2.0,
            "certificates": 2, "valid": 1, "instances": 1,
            "full_certificates": 90, "full_combined_score": 90.5,
            "full_valid": 300, "full_instances": 300, "full_gap_sum": "0"})
        best_screen, best_full = v._current_best()
        self.assertIsNotNone(best_full)
        self.assertEqual(best_full["certificates"], 90)
        self.assertIn("full development 90/100 certificates", v._best_text(best_screen, best_full))

    def test_screen_scope_rows_drive_best_screen(self):
        v = LB.LiftVerifier.__new__(LB.LiftVerifier)
        v.screen, v.full = [None] * 10, [None] * 100
        v.state = {"evaluations": [
            {"scope": "screen", "candidate_hash": "h1", "combined_score": 5.0, "certificates": 3,
             "valid": 10, "instances": 10, "full_certificates": None, "full_combined_score": None,
             "full_valid": None, "full_instances": None, "full_gap_sum": None},
            {"scope": "screen", "candidate_hash": "h2", "combined_score": 6.0, "certificates": 4,
             "valid": 10, "instances": 10, "full_certificates": None, "full_combined_score": None,
             "full_valid": None, "full_instances": None, "full_gap_sum": None},
        ]}
        best_screen, _ = v._current_best()
        self.assertEqual(best_screen["certificates"], 4)  # the better of the two, not the first


class Defect8ResearchStatusExcludesWorkedExamples(unittest.TestCase):
    def test_finalist_only_matching_worked_examples_is_not_new(self):
        seed = {"passes": 0, "violation_sum": "10", "passed_m": []}
        best = {"passes": 2, "violation_sum": "10", "passed_m": [4, 5]}
        status = CB._research_status(seed, best, valid_proposals=["x"], worked_examples=[4, 5])
        self.assertNotEqual(status, "NEW_CERTIFICATES")

    def test_finalist_passing_an_unseen_m_is_new(self):
        seed = {"passes": 0, "violation_sum": "10", "passed_m": []}
        best = {"passes": 3, "violation_sum": "10", "passed_m": [4, 5, 9]}
        status = CB._research_status(seed, best, valid_proposals=["x"], worked_examples=[4, 5])
        self.assertEqual(status, "NEW_CERTIFICATES")

    def test_frozen_manifest_declares_worked_examples(self):
        we = CB.worked_examples_from_manifest(CORR_DIR / 'frozen' / 'manifest.json')
        self.assertEqual(we, [4, 5])


class Defect9EvoxStrategyEvolutionDisabledShort(unittest.TestCase):
    def test_disabled_below_threshold(self):
        self.assertFalse(CB.evox_strategy_evolution_enabled(40, False))
        self.assertFalse(LB.evox_strategy_evolution_enabled(40, False))

    def test_enabled_at_or_above_threshold_unless_overridden(self):
        self.assertTrue(CB.evox_strategy_evolution_enabled(100, False))
        self.assertFalse(CB.evox_strategy_evolution_enabled(100, True))

    def test_sky_config_pushes_switch_interval_past_reach_when_disabled(self):
        # switch_interval, not auto_generate_variation_operators or share_llm,
        # is what actually stops _should_evolve_search() from firing: two
        # smoke runs proved the other two knobs are inert in this launcher
        # (OPENAI_API_BASE is forced to the same broker for the whole
        # sandboxed subprocess regardless of share_llm).
        for mod in (LB, CB):
            with tempfile.TemporaryDirectory() as d:
                args = type('A', (), dict(
                    iterations=6, checkpoint_interval=1, model='m', broker_url='http://x/v1',
                    max_tokens=10, llm_timeout=1, reasoning_effort=None, engine='evox',
                    offline_no_auto_variation=False, evox_switch_interval=2,
                    eval_timeout=1))()
                path = mod._sky_config(args, Path(d))
                cfg = json.loads(path.read_text())
                self.assertGreater(cfg['search']['switch_interval'], args.iterations)
                self.assertFalse(cfg['search']['database']['auto_generate_variation_operators'])
                # a long run keeps the configured interval unchanged
                args.iterations = 200
                cfg = json.loads(mod._sky_config(args, Path(d)).read_text())
                self.assertEqual(cfg['search']['switch_interval'], 2)


class Defect6TruncationFinishReasonReported(unittest.TestCase):
    """finish_reason must reach both the GEPA reflection receipts and lift's
    broker-config.next.json (max_tokens raised 4096->8192, without touching the
    live-ledger-bearing broker-config.json)."""

    def _respond(self, finish_reason):
        def respond(request, timeout):
            body = ('{"choices":[{"message":{"content":"```python\\n'
                    'def propose_words(case):\\n    return []\\n```"},'
                    '"finish_reason":"%s"}]}' % finish_reason).encode()
            return io.BytesIO(body)
        return respond

    def test_lift_broker_lm_receipt_carries_finish_reason(self):
        lm = LB.LiftBrokerLM('http://127.0.0.1:1/v1', 'm', 4096, None, 10, None)
        lm.receipts = []
        with patch.object(LB.ob, 'urlopen', side_effect=self._respond('length')):
            with self.assertRaises(ValueError):  # preflight rejects a truncated proposal
                lm('Improve this lift(instance) program')
        self.assertEqual(lm.receipts[-1]['finish_reason'], 'length')

    def test_corr_broker_lm_receipt_carries_finish_reason(self):
        lm = CB.CorrBrokerLM('http://127.0.0.1:1/v1', 'm', 4096, None, 10, None)
        lm.receipts = []

        def respond(request, timeout):
            body = ('{"choices":[{"message":{"content":"```python\\n'
                    'def coefficients(m):\\n    return {}\\n```"},'
                    '"finish_reason":"stop"}]}').encode()
            return io.BytesIO(body)

        with patch.object(CB.ob, 'urlopen', side_effect=respond):
            lm('Improve this coefficients(m) program')
        self.assertEqual(lm.receipts[-1]['finish_reason'], 'stop')

    def test_lift_next_broker_config_raises_max_tokens_without_touching_applied_one(self):
        applied = json.loads((LIFT_DIR / 'broker-config.json').read_text())
        nxt = json.loads((LIFT_DIR / 'broker-config.next.json').read_text())
        self.assertEqual(applied['max_tokens'], 4096)  # untouched; ledger has real spend
        self.assertEqual(nxt['max_tokens'], 8192)
        # reservation is recomputed by the file's own documented formula, not copy-pasted
        expected = ((nxt['max_prompt_bytes'] + 1024) * nxt['input_usd_per_million'] +
                    (nxt['max_tokens'] + nxt['reasoning_cap_tokens']) * nxt['output_usd_per_million']) / 1e6
        self.assertAlmostEqual(nxt['reservation_usd_per_request_conservative'], expected, places=6)
        self.assertEqual(applied['ledger'], nxt['ledger'])  # never repointed to a new file

    def test_corr_broker_config_already_at_8192(self):
        bc = json.loads((CORR_DIR / 'broker-config.json').read_text())
        self.assertEqual(bc['max_tokens'], 8192)


class EvoxMetaSearchShareReported(unittest.TestCase):
    """SkyDiscover's own client sets no X-LRX-Call-Role header (that header is
    only ever set by our own BrokerLM/_chat clients), so classification must
    come from receipt message content, not a role field."""

    def _write_receipt(self, receipts_dir, idx, messages):
        receipts_dir.mkdir(parents=True, exist_ok=True)
        (receipts_dir / f'attempt-{idx:04d}.json').write_text(
            json.dumps({"forwarded_request_payload": {"messages": messages}}))

    def test_share_computed_from_receipt_content(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / 'ledger.evox.json'
            receipts_dir = Path(d) / 'ledger.evox.json.receipts'
            solution_msg = [{"role": "user", "content": "## Program Information\nImprove lift(instance)."}]
            strategy_msg = [{"role": "user", "content": "Implement class EvolvedProgramDatabase for this "
                                                        "search algorithm's database."}]
            variation_msg = [{"role": "user", "content": "Propose a new variation operator to diverge."}]
            self._write_receipt(receipts_dir, 1, solution_msg)
            self._write_receipt(receipts_dir, 2, solution_msg)
            self._write_receipt(receipts_dir, 3, solution_msg)
            self._write_receipt(receipts_dir, 4, strategy_msg)
            self._write_receipt(receipts_dir, 5, strategy_msg)
            self._write_receipt(receipts_dir, 6, variation_msg)
            evidence = OB._evox_meta_search_share(ledger)
            self.assertEqual(evidence["evox_solution_calls"], 3)
            self.assertEqual(evidence["evox_meta_search_calls"], 3)
            self.assertAlmostEqual(evidence["evox_meta_search_share"], 0.5)

    def test_missing_ledger_reports_none_not_crash(self):
        evidence = OB._evox_meta_search_share(None)
        self.assertIsNone(evidence["evox_meta_search_share"])

    def test_no_role_header_on_real_skydiscover_requests_would_have_broken_the_old_approach(self):
        # SkyDiscover's request messages never carry our custom header; a
        # role-keyed classifier (the pre-fix design) would see nothing and
        # always report share=None even with real receipts on disk.
        self.assertEqual(OB._evox_call_kind([{"role": "user", "content": "## Program Information\nfoo"}]),
                         "solution")
        self.assertEqual(OB._evox_call_kind([{"role": "user", "content": "class EvolvedProgramDatabase, "
                                                                        "search algorithm database"}]),
                         "meta")


class CorrFirstPromptGuardOnAllArms(unittest.TestCase):
    """corr's live rerun (2026-09-25) showed GEPA halts on a first-prompt hash
    mismatch, but sequential/adaevolve/evox had no such guard at all. Fixed
    with CB.first_prompt_mismatch (pre-send, sequential) and
    CB.verify_first_solution_prompt (post-hoc from the arm's own ledger
    receipts, adaevolve/evox -- SkyDiscover's client never passes through
    our Python broker client, so there is no pre-send interception point
    there the way there is for GEPA/sequential)."""

    def test_sequential_first_prompt_mismatch_detected(self):
        messages = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hello"}]
        self.assertTrue(CB.first_prompt_mismatch(messages, "0" * 64))
        self.assertFalse(CB.first_prompt_mismatch(messages, CB.messages_sha256(messages)))

    def test_no_expected_hash_means_nothing_to_check(self):
        messages = [{"role": "user", "content": "hello"}]
        self.assertFalse(CB.first_prompt_mismatch(messages, None))
        self.assertFalse(CB.first_prompt_mismatch(messages, ""))

    def test_adaevolve_evox_post_hoc_check_from_ledger_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / 'ledger.evox.json'
            receipts_dir = Path(d) / 'ledger.evox.json.receipts'
            receipts_dir.mkdir()
            # A bare connectivity probe: ob._evox_call_kind alone (no strategy/
            # variation signal) would default this to "solution" too (the gap
            # sort-task found wiring the identical guard for its own task);
            # _is_corr_solution_request's extra "coefficients" requirement
            # must skip it and not treat it as the first solution prompt.
            probe_msg = [{"role": "user", "content": "ping"}]
            meta_msg = [{"role": "user", "content": "Implement EvolvedProgramDatabase for this "
                                                    "search algorithm's database."}]
            solution_msg = [{"role": "user", "content": "## Program Information\nImprove coefficients(m)."}]
            (receipts_dir / "attempt-0001.json").write_text(
                json.dumps({"forwarded_request_payload": {"messages": probe_msg}}))
            (receipts_dir / "attempt-0002.json").write_text(
                json.dumps({"forwarded_request_payload": {"messages": meta_msg}}))
            (receipts_dir / "attempt-0003.json").write_text(
                json.dumps({"forwarded_request_payload": {"messages": solution_msg}}))
            self.assertEqual(CB.ob._evox_call_kind(probe_msg), "solution")  # confirms the gap exists
            self.assertFalse(CB._is_corr_solution_request(probe_msg))
            expected = CB.messages_sha256(solution_msg)
            actual, matches = CB.verify_first_solution_prompt(ledger, expected)
            self.assertTrue(matches)
            self.assertEqual(actual, expected)
            actual, matches = CB.verify_first_solution_prompt(ledger, "0" * 64)
            self.assertFalse(matches)

    def test_nothing_to_check_without_ledger_or_expected_hash(self):
        self.assertIsNone(CB.verify_first_solution_prompt(None, "0" * 64))
        self.assertIsNone(CB.verify_first_solution_prompt(Path("/nonexistent"), None))

    def test_write_first_prompt_sequential_role_and_system_note(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cap = d / 'cap'
            cap.mkdir()
            messages = [{'role': 'system', 'content': 'SYS'}, {'role': 'user', 'content': 'seq prompt'}]
            (cap / 'request-0001.json').write_text(json.dumps(
                {'role': 'sequential_refinement', 'body': {'model': 'm', 'messages': messages}}))
            digest = CB.write_first_prompt(cap, d / 'out.md', d, role='sequential_refinement',
                                           label='sequential control', has_system_message=True)
            self.assertEqual(digest, CB.messages_sha256(messages))
            text = (d / 'out.md').read_text()
            self.assertIn('separate system message', text)
            self.assertIn(digest, (d / 'out.sha256').read_text())

    def test_write_first_solution_prompt_picks_first_content_classified_solution(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cap = d / 'cap'
            cap.mkdir()
            meta_msg = [{'role': 'user', 'content': 'Implement EvolvedProgramDatabase for this '
                                                    'search algorithm database.'}]
            solution_msg = [{'role': 'user', 'content': '## Program Information\nImprove coefficients(m).'}]
            (cap / 'request-0001.json').write_text(json.dumps(
                {'role': '', 'body': {'model': 'm', 'messages': meta_msg}}))
            (cap / 'request-0002.json').write_text(json.dumps(
                {'role': '', 'body': {'model': 'm', 'messages': solution_msg}}))
            digest = CB.write_first_solution_prompt(cap, d / 'out.md', d, label='evox')
            self.assertEqual(digest, CB.messages_sha256(solution_msg))

    def test_approval_material_includes_all_four_prompt_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            shutil.copyfile(CORR_DIR / 'broker-config.json', d / 'broker-config.json')
            shutil.copyfile(CORR_DIR / 'campaign-config.json', d / 'campaign-config.json')
            for name in ('first-prompt.sha256', 'first-prompt-sequential.sha256',
                        'first-prompt-adaevolve.sha256', 'first-prompt-evox.sha256'):
                (d / name).write_text(('0' * 64) + '  x\n')
            material = CB.approval_material(d / 'broker-config.json', d / 'campaign-config.json')
            for key in ('first_prompt_sha256', 'first_prompt_sequential_sha256',
                       'first_prompt_adaevolve_sha256', 'first_prompt_evox_sha256'):
                self.assertEqual(material[key], '0' * 64)


class CorrFinalizeModeOnlyAdmission(unittest.TestCase):
    """Ported from integrations/sort_finalize.py: a FIRST_PROMPT_MISMATCH arm whose first
    solution prompt differs from the approved capture ONLY in SkyDiscover's unseeded
    parent-selection mode-guidance block should still be admitted as a finalist."""

    def test_mode_only_difference_admits(self):
        from integrations import corr_finalize as CF
        sysmsg = {"role": "system", "content": "SYS"}
        captured_user = {"role": "user", "content": "before\n" + CF.MODE_LABELS[0] + "\nafter"}
        live_user = {"role": "user", "content": "before\n" + CF.MODE_LABELS[1] + "\nafter"}
        ok, diff, reason = CF.mode_only_difference([sysmsg, live_user], [sysmsg, captured_user])
        self.assertTrue(ok, reason)
        self.assertIn("mode-guidance", reason)

    def test_content_change_outside_mode_block_is_refused(self):
        from integrations import corr_finalize as CF
        sysmsg = {"role": "system", "content": "SYS"}
        captured_user = {"role": "user", "content": "def coefficients(m): return OLD"}
        live_user = {"role": "user", "content": "def coefficients(m): return NEW"}
        ok, diff, reason = CF.mode_only_difference([sysmsg, live_user], [sysmsg, captured_user])
        self.assertFalse(ok)

    def test_report_handles_admitted_mismatch_arm_in_runs(self):
        # Regression: _report crashed with "too many values to unpack (expected 4)"
        # once admission grew the runs tuple to 7 elements (ValueError in finalize-v2
        # console log). _report must accept the wider tuple.
        from integrations import corr_finalize as CF
        arm = "adaevolve"
        admitted = {"rule": "only the mode-guidance block differs", "live_sha256": "a" * 64,
                   "captured_sha256": "b" * 64, "live_receipt": "x", "unified_diff": "diff"}
        manifest = {"mechanism_evidence": {"configured_iterations": 4}}
        runs = {arm: ((2, Fr(-216322)), Path("/run"), manifest, Path("/src"), "c" * 64,
                     {"passes": 2, "violation_sum": "216322", "combined_score": 2.0}, admitted)}
        finalists = [{"arm": arm, "run_dir": "/run", "source": "/src", "source_sha256": "c" * 64,
                     "development_claim": {"passes": 2}, "admitted_with_prompt_mismatch": admitted}]
        dev_row = {"passes": 2, "m_values": 9, "results": [{"m": 4, "passed": False, "magnitude": "5"}]}
        hold_row = {"passes": 0, "m_values": 8, "results": [{"m": 13, "passed": False, "magnitude": "3"}]}
        naive_dev = {"passes": 0, "m_values": 9, "results": [{"m": 4, "passed": False, "magnitude": "9"}]}
        naive_hold = {"passes": 0, "m_values": 8, "results": [{"m": 13, "passed": False, "magnitude": "9"}]}
        results = {"development": {"arms": {arm: dev_row, "naive-control": naive_dev}},
                  "holdout": {"arms": {arm: hold_row, "naive-control": naive_hold}}}
        audit_row = {"agree": 2, "claimed": 2, "disagree": []}
        audit = {"development": {arm: audit_row}, "holdout": {arm: dict(audit_row, agree=0, claimed=0)}}
        ledger = {arm: {"attempts": 5, "usd": 0.01, "truncated": 0}}
        frozen_set = {"evaluator": {"version": "v1"}, "development_sha256": "d" * 64,
                      "holdout_sha256": "e" * 64}
        report = CF._report(finalists, runs, results, audit, ledger, frozen_set)
        self.assertIn("adaevolve", report)
        self.assertIn("configured_iterations", report)

    def test_parse_first_prompt_md_round_trips_write_first_solution_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            messages = [{"role": "system", "content": "SYS line"},
                       {"role": "user", "content": "## Program Information\ndef coefficients(m): pass"}]
            cap = d / 'cap'
            cap.mkdir()
            (cap / 'request-0001.json').write_text(json.dumps(
                {'role': '', 'body': {'model': 'm', 'max_tokens': 10, 'messages': messages}}))
            from integrations import corr_finalize as CF
            digest = CB.write_first_solution_prompt(cap, d / 'out.md', d, label='evox')
            parsed = CF._parse_first_prompt_md(d / 'out.md')
            self.assertEqual(CB.messages_sha256(parsed), digest)
            self.assertEqual(parsed, messages)


if __name__ == '__main__':
    unittest.main()
