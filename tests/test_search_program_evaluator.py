"""Focused proof, failure, and (opt-in) OS-isolation checks."""
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from integrations.mixture_lp import optimize
from integrations.program_evaluator import ProgramEvaluator, _direct_materialize, _direct_profile, _feasible_base, _verified_dual
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

    def test_frozen_allcuts_incumbent_protects_fifteen_and_checks_exact_dual(self):
        frozen = ROOT / 'autoresearch/official-integration-260924/frozen'
        cases = json.loads((frozen / 'development.json').read_text())
        baseline = json.loads((frozen / 'development-baseline.json').read_text())
        allcuts = json.loads((ROOT / 'autoresearch/loop-260924-live/offline-allcuts'
                             / '3fcc0f0d23ced3f0-evaluation.json').read_text())
        incumbent = {row['case']['id']: [item['profile'] for item in row['accepted_words']]
                     for row in allcuts['families']}
        dual = {'k5-mask302-order15713': {
            'tight': [1, 2, 3, 4], 'mu': ['11/14', '197/196', '1/8', '261/392'],
            'nu': '30221/392'}}
        evaluator = ProgramEvaluator(cases, baseline, incumbent=incumbent, dual=dual,
                                     require_os_sandbox=False)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'empty.py'
            path.write_text('def propose_words(case):\n    return []\n')
            result = evaluator.evaluate(path)
            path.write_text('def propose_words(case):\n    raise RuntimeError("invalid")\n')
            failed = evaluator.evaluate(path)
        self.assertEqual(result['incumbent_certified'], 15)
        self.assertEqual(result['certified'], 15)
        self.assertEqual(result['new_vs_catalog'], 3)
        self.assertEqual(result['new_vs_incumbent'], 0)
        self.assertEqual(result['combined_score'], 0)
        self.assertEqual(result['certificate_weight'], 1001)
        self.assertEqual(failed['certified'], 15)
        self.assertEqual(failed['new_vs_incumbent'], 0)
        self.assertEqual(failed['secondary_score'], '0')
        self.assertEqual(failed['combined_score'], -16)
        miss = next(row for row in result['families'] if row['case']['id'] == 'k5-mask302-order15713')
        self.assertFalse(miss['incumbent_certified'])
        self.assertEqual(miss['progress']['feasible_base_before'], '24149/392')
        self.assertEqual(miss['progress']['base_deficit_after'], '237/392')
        ada = json.loads((ROOT / 'autoresearch/loop-260924-live/adaevolve-low/verified/evaluations'
                          / 'result-0002.json').read_text())
        ada_row = next(r for r in ada['families'] if r['case']['id'] == miss['case']['id'])
        old_profiles = {(p['base'], tuple(p['gamma'])) for p in incumbent[miss['case']['id']]}
        added = [item['profile'] for item in ada_row['accepted_words']
                 if (item['profile']['base'], tuple(item['profile']['gamma'])) not in old_profiles]
        def reduced(p):
            g = p['gamma']
            return (Fraction(p['base']) + Fraction(11, 14)*g[1]
                    + Fraction(197, 196)*g[2] + Fraction(1, 8)*g[3]
                    + Fraction(261, 392)*g[4] - Fraction(30221, 392))
        best = min(added, key=reduced)
        worst = max(added, key=reduced)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'one_word.py'
            path.write_text('def propose_words(case):\n    return ' + repr([worst['word'], best['word']]) + '\n')
            single = ProgramEvaluator([miss['case']], baseline, incumbent=incumbent, dual=dual,
                                      require_os_sandbox=False).evaluate(path)
        grade = single['families'][0]['progress']
        self.assertEqual(grade['best_reduced_cost'], str(reduced(best)))
        self.assertEqual(grade['best_reduced_cost'], '5275/196')
        self.assertEqual(grade['best_useful_words'][0]['word'], best['word'])
        self.assertEqual(grade['secondary_grade'], '0')
        self.assertEqual(single['combined_score'], 0)
        tampered = {'k5-mask302-order15713': dict(dual['k5-mask302-order15713'], nu='30222/392')}
        with self.assertRaisesRegex(ValueError, 'objective disagree'):
            ProgramEvaluator(cases, baseline, incumbent=incumbent, dual=tampered,
                             require_os_sandbox=False)

    def test_exact_partial_progress_without_certificate_and_invalid_gate(self):
        frozen = ROOT / 'autoresearch/official-integration-260924/frozen'
        cases = json.loads((frozen / 'development.json').read_text())
        baseline = json.loads((frozen / 'development-baseline.json').read_text())
        case = next(c for c in cases if c['id'] == 'k4-mask432-order21829')
        # A real two-column incumbent has a feasible intercept above 55.
        reference = {case['id']: [baseline[case['id']][0], baseline[case['id']][3]]}
        allcuts = json.loads((ROOT / 'autoresearch/loop-260924-live/offline-allcuts'
                             / '3fcc0f0d23ced3f0-evaluation.json').read_text())
        row = next(r for r in allcuts['families'] if r['case']['id'] == case['id'])
        useful = next(item['profile']['word'] for item in row['accepted_words']
                      if item['profile']['word'].startswith('XLXRXRRRXRXRRXRXRXRXRXRXRX'))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'candidate.py'
            evaluator = ProgramEvaluator([case], reference, incumbent={}, require_os_sandbox=False)
            path.write_text('def propose_words(case):\n    return ' + repr([useful]) + '\n')
            partial = evaluator.evaluate(path)
            path.write_text('def propose_words(case):\n    return ["X"] * 33\n')
            invalid = evaluator.evaluate(path)
            path.write_text('def propose_words(case):\n    return 7\n')
            wrong_type = evaluator.evaluate(path)
        progress = partial['families'][0]['progress']
        self.assertEqual(partial['new_vs_incumbent'], 0)
        self.assertEqual(partial['families'][0]['status'], 'NO_CERTIFICATE')
        self.assertEqual((progress['feasible_base_before'], progress['feasible_base_after']),
                         ('395/7', '56'))
        self.assertEqual(progress['base_improvement'], '3/7')
        self.assertEqual(progress['base_deficit_after'], '1')
        self.assertFalse(progress['strict_base_pass'])
        self.assertEqual(progress['secondary_grade'], '3/20')
        self.assertTrue(0 < partial['combined_score'] < 1)
        self.assertEqual(invalid['combined_score'], -1)
        self.assertEqual(invalid['families'][0]['progress']['secondary_grade'], '0')
        self.assertIn('33 words; limit 32', invalid['families'][0]['candidate_run']['reason'])
        self.assertEqual(wrong_type['families'][0]['candidate_run']['actual_type'], 'int')
        self.assertEqual(wrong_type['combined_score'], -1)

    def test_negative_reduced_cost_is_necessary_not_a_certificate(self):
        # An exact LP example separates improving an old pool from crossing
        # the strict family bound. The verifier never treats a dual hint as proof.
        old = [{'base': 40, 'gamma': [6]}, {'base': 45, 'gamma': [0]}]
        old_result = optimize(old)
        dual = _verified_dual(old, old_result,
                              {'tight': [0], 'mu': ['0'], 'nu': '40'}, 1)
        new_profile = {'base': 39, 'gamma': [6]}
        self.assertEqual(dual['reduced_cost'](new_profile), Fraction(-1))
        improved = optimize(old + [new_profile])
        self.assertEqual(improved['base'], '39')
        self.assertEqual(improved['status'], 'NO_CERTIFICATE')
        with self.assertRaisesRegex(ValueError, 'primal base'):
            _feasible_base(dict(improved, base='38'), old + [new_profile])
        with self.assertRaisesRegex(ValueError, 'primal slopes'):
            _feasible_base({'base': '39', 'weights': ['0', '0', '1']},
                           old + [{'base': 39, 'gamma': [7]}])

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
