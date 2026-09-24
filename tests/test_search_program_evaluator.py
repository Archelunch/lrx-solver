"""Focused proof, failure, and (opt-in) OS-isolation checks."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from integrations.program_evaluator import ProgramEvaluator, _direct_materialize, _direct_profile
from integrations.program_seed import propose_words
from integrations.projected_mixtures import state_for


ROOT = Path(__file__).resolve().parents[1]
CASE = {'id': 'canonical-four', 'm': 8, 'labels': list(range(1, 9)),
        'mask': 480, 'blocks': 4}
VALID_WORD = propose_words(CASE)[0]


class ProgramEvaluatorTests(unittest.TestCase):
    def _candidate(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'candidate.py'
            path.write_text(text, encoding='utf-8')
            return ProgramEvaluator([CASE], require_os_sandbox=False, **kwargs).evaluate(path)

    def test_direct_word_recomputes_cost_and_lifts(self):
        state = state_for(CASE['labels'], CASE['mask'])
        profile = _direct_profile(state, VALID_WORD + 'XX')
        self.assertEqual(profile['base'], len(VALID_WORD) + 2)
        audit = _direct_materialize(profile, [1, 2, 3, 4])
        self.assertLessEqual(audit['length'], audit['upper'])

    def test_normalizes_inverse_rotations_and_zero_zero_swaps(self):
        state = state_for(CASE['labels'], CASE['mask'])
        profile = _direct_profile(state, VALID_WORD + 'LLLLLLLLXRRRRRRRR')
        self.assertEqual(profile['word'], VALID_WORD)
        self.assertEqual(profile['base'], len(VALID_WORD))

    def test_complete_constructor_can_certify_canonical_family(self):
        frozen = ROOT / 'autoresearch' / 'official-integration-260924' / 'frozen'
        cases = json.loads((frozen / 'development.json').read_text())
        baseline = json.loads((frozen / 'development-baseline.json').read_text())
        target = next(c for c in cases if c['id'] == 'k5-mask333-order27563')
        result = ProgramEvaluator([target], baseline, require_os_sandbox=False).evaluate(
            ROOT / 'integrations' / 'program_seed.py')
        self.assertEqual(result['new_certified'], 1)
        row = result['families'][0]
        self.assertEqual(row['status'], 'CERTIFICATE')
        self.assertGreater(len(row['accepted_words']), 0)
        self.assertFalse(row['baseline_certified'])

    def test_rejects_false_word_and_tampered_baseline(self):
        result = self._candidate('def propose_words(case):\n    return ["X"]\n')
        self.assertEqual(result['new_certified'], 0)
        self.assertEqual(len(result['families'][0]['rejected_words']), 1)
        state = state_for(CASE['labels'], CASE['mask'])
        with self.assertRaisesRegex(ValueError, 'asserted profile'):
            ProgramEvaluator([CASE], {CASE['id']: [{
                'kind': 'direct', 'state': list(state), 'target': list(state),
                'word': VALID_WORD, 'base': 1, 'gamma': [0, 0, 0, 0],
            }]}, require_os_sandbox=False)

    def test_error_timeout_and_output_cap_remain_incomplete(self):
        error = self._candidate('def propose_words(case):\n    raise RuntimeError("boom")\n')
        self.assertEqual(error['families'][0]['status'], 'candidate_error')
        timeout = self._candidate('def propose_words(case):\n    while True: pass\n',
                                  timeout_seconds=0.3)
        self.assertEqual(timeout['families'][0]['status'], 'INCOMPLETE')
        self.assertEqual(timeout['families'][0]['candidate_run']['reason'], 'time limit')
        oversized = self._candidate('def propose_words(case):\n    return ["LR"] * 33\n')
        self.assertEqual(oversized['families'][0]['status'], 'INVALID_OUTPUT')
        malformed = self._candidate('def propose_words(case):\n    return 7\n')
        self.assertEqual(malformed['families'][0]['status'], 'INVALID_OUTPUT')

    def test_source_is_bounded_regular_and_snapshotted(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'candidate.py'
            good = b'def propose_words(case):\n    return []\n'
            path.write_bytes(good)
            second = dict(CASE, id='second')
            evaluator = ProgramEvaluator([CASE, second], require_os_sandbox=False)
            original = evaluator._run_case

            def change_file_after_snapshot(source_bytes, case):
                path.write_text('def propose_words(case):\n    raise RuntimeError("changed")\n')
                return original(source_bytes, case)

            evaluator._run_case = change_file_after_snapshot
            result = evaluator.evaluate(path)
            self.assertEqual(result['candidate_hash'], hashlib.sha256(good).hexdigest())
            self.assertTrue(all(row['candidate_run']['status'] == 'ok'
                                for row in result['families']))
            link = Path(d) / 'link.py'
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, 'regular'):
                evaluator.evaluate(link)
            path.write_bytes(b'x' * 65537)
            with self.assertRaisesRegex(ValueError, 'byte cap'):
                evaluator.evaluate(path)

    @unittest.skipUnless(os.environ.get('LRX_TEST_SANDBOX') == '1',
                         'requires explicit macOS sandbox test outside Codex outer sandbox')
    def test_os_denies_confirmation_read_and_evaluator_write(self):
        evaluator_file = ROOT / 'integrations' / 'program_evaluator.py'
        before = hashlib.sha256(evaluator_file.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='lrx-protected-', dir=ROOT) as d:
            secret = Path(d) / '.env'
            confirmation = Path(d) / 'confirmation.json'
            secret.write_text('SECRET_SHOULD_NOT_LEAK', encoding='utf-8')
            confirmation.write_text('{"hidden": true}', encoding='utf-8')
            candidate = Path(d) / 'attack.py'
            candidate.write_text(
                'def propose_words(case):\n'
                '    from pathlib import Path\n'
                f'    files = {json.dumps([str(secret), str(confirmation)])}\n'
                '    breached = False\n'
                '    for name in files:\n'
                '        try: Path(name).read_text(); breached = True\n'
                '        except OSError: pass\n'
                f'    try: Path({str(evaluator_file)!r}).write_text("hacked"); breached = True\n'
                '    except OSError: pass\n'
                '    return ["X"] if breached else []\n', encoding='utf-8')
            result = ProgramEvaluator([CASE]).evaluate(candidate)
        self.assertEqual(result['isolation'], 'macos_seatbelt')
        self.assertEqual(result['families'][0]['status'], 'NO_CERTIFICATE')
        self.assertEqual(result['families'][0]['rejected_words'], [])
        self.assertEqual(hashlib.sha256(evaluator_file.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
