"""Fast tests for the corr-cert engine plumbing (autoresearch/corr-cert-260924/TASK.md)."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction as Fr
from itertools import combinations

from integrations import corr_task as T
from integrations import corr_evaluator as E
from integrations import corr_backends as B

SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'
ROOT = Path(__file__).resolve().parents[1]
CORR_DIR = ROOT / 'autoresearch' / 'corr-cert-260924'


def exact_m4_cert():
    """The group's exact epsilon=0 certificate for m=4 (THEOREM.md observations,
    lambda solved here from the forced-tightness constraint, alpha=beta=gamma=0)."""
    m, Q = 4, 1
    mu = {0: [4 * (q - 3) for q in range(1, m)], 1: [4 * (q - 2) for q in range(1, m)],
          2: [-4 * (q - 2) for q in range(1, m)], 3: [-4 * (q - 1) for q in range(1, m)]}
    lam = {}
    for a in range(m):
        for b in range(a + 1, m):
            lam[(a, b)] = min(Q * T.corrcert.kappa(m, a, b, q) - mu[a][q - 1] - mu[b][m - q - 1]
                              for q in range(1, m))
    zero = {t: [0] * (m - 1) for t in combinations(range(m), 3)}
    return {'m': m, 'Q': Q, 'lambda': lam, 'mu': mu, 'alpha': dict(zero), 'beta': dict(zero), 'gamma': dict(zero)}


class KeyEncodingTest(unittest.TestCase):
    def test_round_trip_exact_certificate(self):
        cert = exact_m4_cert()
        raw = T.encode_cert(cert)
        self.assertEqual(set(raw['lambda']), {'0,1', '0,2', '0,3', '1,2', '1,3', '2,3'})
        self.assertEqual(set(raw['mu']), {'0', '1', '2', '3'})
        self.assertEqual(set(raw['alpha']), {'0,1,2', '0,1,3', '0,2,3', '1,2,3'})
        self.assertTrue(all(isinstance(k, str) for k in raw['lambda']) and
                        all(isinstance(v, int) for v in raw['lambda'].values()))
        self.assertEqual(T.decode_cert(4, raw), cert)
        # the checker itself still passes on the round-tripped certificate
        res = T.corrcert.check_certificate(4, T.decode_cert(4, raw))
        self.assertTrue(res['proves'])
        self.assertEqual(res['epsilon'], 0)

    def test_decode_rejects_bad_shapes(self):
        good = T.encode_cert(exact_m4_cert())
        with self.assertRaises(ValueError):
            T.decode_cert(4, {**good, 'm': 5})  # m mismatch
        with self.assertRaises(ValueError):
            T.decode_cert(4, {**good, 'Q': 0})  # non-positive Q
        with self.assertRaises(ValueError):
            T.decode_cert(4, {**good, 'lambda': {**good['lambda'], '0,1': 1.5}})  # float, not int
        bad_key = dict(good['lambda']); del bad_key['0,1']; bad_key['0,1,2'] = 0
        with self.assertRaises(ValueError):
            T.decode_cert(4, {**good, 'lambda': bad_key})  # wrong arity key
        with self.assertRaises(ValueError):
            T.decode_cert(4, [1, 2, 3])  # not a dict at all

    def test_m_set_guard_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'development.json'
            T.write_m_set(p, 'development', T.DEVELOPMENT_M)
            self.assertEqual(T.load_m_set(p), list(range(4, 13)))
            T.guard_not_holdout(p)  # does not raise
            h = Path(d) / 'holdout.json'
            T.write_m_set(h, 'holdout', T.HOLDOUT_M)
            with self.assertRaises(ValueError):
                T.guard_not_holdout(h)
            bad = Path(d) / 'bad.json'
            bad.write_text(json.dumps({'schema': 'wrong', 'set': 'development', 'm_values': [4]}))
            with self.assertRaises(ValueError):
                T.load_m_set(bad)


class ScoringTest(unittest.TestCase):
    """score_m operates on a worker attempt dict directly, so these need no subprocess/sandbox."""

    def test_pass_on_exact_certificate(self):
        raw = T.encode_cert(exact_m4_cert())
        row = E.score_m(4, {'status': 'ok', 'output': raw})
        self.assertEqual(row['status'], 'PASS')
        self.assertTrue(row['passed'])
        self.assertEqual(row['magnitude'], '0')
        self.assertEqual(row['epsilon'], '0')

    def test_fail_on_corrupted_certificate(self):
        cert = exact_m4_cert()
        cert['lambda'][(0, 1)] += 100  # break pair condition (6) at (0,1): P_ab(q) exceeds Q*kappa
        row = E.score_m(4, {'status': 'ok', 'output': T.encode_cert(cert)})
        self.assertEqual(row['status'], 'FAIL')
        self.assertFalse(row['passed'])
        self.assertGreater(Fr(row['magnitude']), 0)
        self.assertTrue(row['violations'])
        self.assertIn(row['violations'][0][0], ('pair6', 'triple5'))

    def test_invalid_output_shapes(self):
        for bad in ({'lambda': {}}, {'m': 5}, None, 42, {'m': 4, 'Q': 'x'}):
            row = E.score_m(4, {'status': 'ok', 'output': bad})
            self.assertEqual(row['status'], 'INVALID_OUTPUT')
            self.assertFalse(row['passed'])
            self.assertEqual(row['magnitude'], E.INVALID_GAP)

    def test_crash_and_timeout_are_never_evidence(self):
        for attempt in ({'status': 'candidate_error', 'error': 'ValueError: boom'},
                        {'status': 'INCOMPLETE', 'reason': 'time limit'}):
            row = E.score_m(4, attempt)
            self.assertEqual(row['status'], attempt['status'])
            self.assertFalse(row['passed'])
            self.assertEqual(row['magnitude'], E.INVALID_GAP)

    def test_evaluator_hash_is_stable_and_program_size_cap(self):
        h1, h2 = E.evaluator_hash(), E.evaluator_hash()
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
        with tempfile.TemporaryDirectory() as d:
            big = Path(d) / 'candidate.py'
            big.write_text('def coefficients(m): return {}\n' + '#' * (E.MAX_SOURCE + 1))
            with self.assertRaises(ValueError):
                E.evaluate(big, [4], require_os_sandbox=False)


class ApprovalHashTest(unittest.TestCase):
    def test_check_approval_refuses_without_file(self):
        # Copy the real configs into a fresh temp dir so this test's outcome never depends on
        # whether a real payload-approved.sha256 happens to sit next to the live configs.
        with tempfile.TemporaryDirectory() as d:
            broker = Path(d) / 'broker-config.json'
            broker.write_text((CORR_DIR / 'broker-config.json').read_text())
            campaign = Path(d) / 'campaign-config.json'
            campaign.write_text((CORR_DIR / 'campaign-config.json').read_text())
            self.assertFalse((Path(d) / 'payload-approved.sha256').exists())
            with self.assertRaises(SystemExit):
                B.check_approval(broker, campaign)

    def test_approval_hash_is_deterministic_and_covers_configs(self):
        h1 = B.approval_hash(CORR_DIR / 'broker-config.json', CORR_DIR / 'campaign-config.json')
        h2 = B.approval_hash(CORR_DIR / 'broker-config.json', CORR_DIR / 'campaign-config.json')
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
        material = B.approval_material(CORR_DIR / 'broker-config.json', CORR_DIR / 'campaign-config.json')
        self.assertIn('system_prompt', material)
        self.assertIn('objective', material)
        self.assertEqual(material['packet_format']['marker'], B.PACKET_MARK)
        # changing the broker cap changes the hash (the whole config is covered, not just a subset)
        with tempfile.TemporaryDirectory() as d:
            mutated = json.loads((CORR_DIR / 'broker-config.json').read_text())
            mutated['max_usd'] = 999
            p = Path(d) / 'broker-config.json'
            p.write_text(json.dumps(mutated))
            h3 = B.approval_hash(p, CORR_DIR / 'campaign-config.json')
            self.assertNotEqual(h1, h3)


class PacketTest(unittest.TestCase):
    def _fake_result(self, n_fail=9):
        results = []
        for i, m in enumerate(range(4, 4 + n_fail)):
            results.append({'m': m, 'passed': False, 'status': 'FAIL', 'epsilon': str(-10 - i),
                            'violations': [['pair6', 0, 1, None, 1, None, -24 - i],
                                          ['triple5', 0, 1, 2, 1, 2, -5],
                                          ['pair6', 0, 2, None, 2, None, -3]]})
        return {'m_values': list(range(4, 4 + n_fail)), 'passes': 0,
                'violation_sum': str(sum(24 + i for i in range(n_fail))), 'results': results}

    def test_packet_within_size_and_carries_marker_and_reminder(self):
        text = B.packet(self._fake_result(), 'none')
        self.assertLessEqual(len(text), B.PACKET_MAX)
        self.assertIn(B.PACKET_MARK, text)
        self.assertIn('development only', text)

    def test_packet_truncates_gracefully_when_many_m_fail(self):
        # many failing m with verbose violation text must still respect the cap
        text = B.packet(self._fake_result(n_fail=9), 'best-so-far text ' * 5)
        self.assertLessEqual(len(text), B.PACKET_MAX)
        self.assertTrue(text)  # never truncated to nothing

    def test_preflight_source_shape(self):
        good = "```python\ndef coefficients(m):\n    return {}\n```"
        self.assertIn('def coefficients', B.preflight_source(good))
        with self.assertRaises(ValueError):
            B.preflight_source("no fence here")
        with self.assertRaises(ValueError):
            B.preflight_source("```python\ndef other(m): return {}\n```")  # missing coefficients()
        with self.assertRaises(ValueError):
            B.preflight_source("text\n```python\ndef coefficients(m): return {}\n```")  # extra prose
        with self.assertRaises(ValueError):
            B.preflight_source("```python\ndef coefficients(m): return {}\n```", finish_reason='length')


@unittest.skipUnless(SANDBOX, 'set LRX_TEST_SANDBOX=1 to exercise the sandboxed evaluate() path')
class SandboxedEvaluateTest(unittest.TestCase):
    def test_seed_program_runs_under_sandbox(self):
        seed = ROOT / 'integrations' / 'corr_control_f1.py'
        res = E.evaluate(seed, [4, 5], require_os_sandbox=True, jobs=2)
        self.assertEqual(res['isolation'], 'macos_seatbelt')
        self.assertEqual(len(res['results']), 2)
        self.assertEqual(res['passes'], 0)  # the seed is known not to pass; see TASK.md

    def test_malformed_candidate_scores_invalid_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad.py'
            bad.write_text('def coefficients(m):\n    return "not a dict"\n')
            res = E.evaluate(bad, [4], require_os_sandbox=True, jobs=1)
            self.assertEqual(res['results'][0]['status'], 'INVALID_OUTPUT')
            self.assertEqual(res['passes'], 0)


if __name__ == '__main__':
    unittest.main()
