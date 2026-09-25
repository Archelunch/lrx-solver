"""Fast tests for the m-parametric lift evaluator (autoresearch/lift-m9-260924/TASK.md)."""
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction as Fr

from integrations import lift_evaluator as E
from integrations import lift_task as T
from integrations import lrx_m as C

V8 = [0, 5, 0, 8, 7, 0, 6, 4, 3, 2, 1, 0]
LABELS, MASK = [5, 8, 7, 6, 4, 3, 2, 1], 0b100001011
W1 = 'XLLXLXRRXRRXLXLLXRXRXRRRXRXRXRXLXLXLXLXRRXRXLXRR'
W2 = 'LXLLLXLLXRXLLXRXRXRRXRXLLXLXLLXLXRXRXRXRXRXLXLXLLXLXLXRXRXRXRXRXRX'
CONTROL = Path(__file__).resolve().parents[1] / 'integrations' / 'lift_control_naive.py'
SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'


def parent():
    rows = [T.plain_row(LABELS, MASK, W1, '5/8'), T.plain_row(LABELS, MASK, W2, '3/8')]
    return {'id': 'ex8', 'labels': LABELS, 'mask': MASK, 'certificate': {'kind': 'mixture', 'rows': rows}}


class LiftEvalTest(unittest.TestCase):
    def test_m_generalization_reproduces_section8_example(self):
        self.assertEqual(C.base_vector(LABELS, MASK), V8)
        p1, p2 = C.Profile(V8, W1), C.Profile(V8, W2)
        self.assertEqual((p1.base, p1.beta, p2.base, p2.beta), (48, [9, 6, 0, 8], 66, [1, 2, 8, 0]))
        C.literal_lift_check(p1, C.z_samples(4))
        ok, B, beta = C.mixture_criterion([(48, p1.beta), (66, p2.beta)], ['5/8', '3/8'], 4, m=8)
        self.assertTrue(ok)
        self.assertEqual((B, beta), (Fr(219, 4), [6, Fr(9, 2), 3, 5]))
        self.assertEqual([C.budget(9, k) for k in (4, 6)], [66, 80])
        self.assertEqual(C.budget(8, 4) + 1, 31 + 6 * 4)
        self.assertTrue(C.is_root(list(range(1, 10)) + [0, 0]))

    def test_instance_construction(self):
        inst = T.build_instance(parent(), 1, 'both')
        self.assertEqual(inst['id'], 'lift-ex8-i1-both')
        ch = inst['child']
        self.assertEqual(ch['labels'], [5, 9, 8, 7, 6, 4, 3, 2, 1])
        self.assertEqual(ch['unit_base'], [0, 5, 0, 9, 0, 8, 7, 0, 6, 4, 3, 2, 1, 0])
        self.assertEqual((ch['k'], ch['budget_unit'], ch['slope_bound']), (5, 73, 7))
        self.assertEqual(ch['id'], 'm9-mask%d-labels598764321' % ch['mask'])
        self.assertEqual(T.child_family(LABELS, MASK, 2, 'none')[1], 0b1000010011)
        with self.assertRaises(ValueError):
            T.child_family(LABELS, MASK, 2, 'left')  # gap 2 is empty
        self.assertEqual(len(T.build_instances(parent())), 4 * 3 + 5)
        want, rows = T.check_instance(inst)
        self.assertEqual([r['base'] for r in rows], [48, 66])

    def test_exact_lp_toy(self):
        costs = [(10, [3, 0]), (4, [9, 1]), (7, [5, 5]), (20, [0, 0])]
        w, B, s, t = E.mixture_lp(costs, 2, 6)
        best = min(a * p + (1 - a) * q for (p, bp), (q, bq) in itertools.combinations(costs, 2)
                   for a in [Fr(i, 60) for i in range(61)]
                   if all(a * x + (1 - a) * y <= 6 for x, y in zip(bp, bq)))
        self.assertEqual((B, t), (best, 0))
        self.assertEqual((sum(w), max(s) <= 6), (1, True))
        w, B, s, t = E.mixture_lp([(5, [9]), (6, [8])], 1, 7)
        self.assertEqual((t, B, s), (1, 6, [8]))
        self.assertEqual(E.simplex([[1, 1]], [-1], [1, 1])[0], 'infeasible')

    def _instances(self, n=3):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'sample.json'
            path.write_text(json.dumps({'schema': 'lrx-lift-instances-v1',
                                        'instances': T.build_instances(parent())[:n]}))
            return E.load_instances(path)

    def test_naive_control_is_valid(self):
        res = E.evaluate(CONTROL, self._instances(), require_os_sandbox=SANDBOX, jobs=3)
        self.assertEqual((res['instances'], res['valid'], res['invalid']), (3, 3, 0))
        r = res['results'][0]
        self.assertEqual(r['status'], 'NO_CERTIFICATE')
        self.assertEqual(r['trace']['parent_rows_used'], [0, 1])
        self.assertGreater(Fr(r['gap']), 0)

    def test_invalid_output_is_failure_not_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad.py'
            bad.write_text("def lift(instance):\n    return {'words': ['L', 'LLX']}\n")
            many = Path(d) / 'many.py'
            many.write_text("def lift(instance):\n    return {'words': ['X'] * 17}\n")
            inst = self._instances(1)
            r = E.evaluate(bad, inst, require_os_sandbox=SANDBOX)
            self.assertEqual((r['valid'], r['certificates'], r['gap_sum']), (0, 0, str(E.INVALID_GAP)))
            self.assertEqual(r['results'][0]['status'], 'INVALID_OUTPUT')
            self.assertEqual(r['results'][0]['trace']['failed_word']['index'], 0)
            r = E.evaluate(many, inst, require_os_sandbox=SANDBOX)
            self.assertIn('17 words', r['results'][0]['trace']['failure'])


if __name__ == '__main__':
    unittest.main()
