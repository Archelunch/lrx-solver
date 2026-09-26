"""Tests for bound-eval-3 tree certificates (integrations/bound3_*.py). No provider calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from integrations import bound3_audit as A
from integrations import bound3_evaluator as B3
from integrations import bound3_task as K
from integrations import bound_control_sweep as sweep
from integrations import bound_evaluator as E
from integrations import lrx_m as C
from integrations.bound_task import make_family

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / 'autoresearch' / 'bound-m-260925' / 'frozen' / 'development.json'
ADA = ROOT / 'autoresearch' / 'bound-m-c2-260925' / 'finalists' / 'development-arms' / 'adaevolve-s2.json'
SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'
REV84 = make_family([8, 7, 6, 5, 4, 3, 2, 1], 1 | 16)
# The research group's tree for (8..1){0,4} (reverse certificates file, 2026-09-23): split u_0 <= 1,
# then u_0 <= 2; one word on the unit base near the corner, two words at origin (3,1) beyond.
W34 = 'LXLXRXRXLXLXLXRXRXRXRRRXRXLXLXRXRX'
W52 = 'LLXLXLXRXRXRXRXLLXLXRXRXLXLLLLXLXLXLXLXRXRXRXLXLXRXR'
W55 = 'RXLXLXLLLLXLLXRXRXRXLXLXLLXRXRXRXRXRXLXLXLXLXLLLXLXLXLX'
GROUP = {'tree': {'j': 0, 't': 1, 'le': {'words': [W34]},
                  'ge': {'j': 0, 't': 2, 'le': {'words': [W34]},
                         'ge': {'words': [W52, W55], 'origins': [3, 1], 'weights': ['1/3', '2/3']}}}}


def dev_sample(n=20):
    fams = E.load_set(DEV)
    return [fams[i] for i in range(0, len(fams), len(fams) // n)][:n]


def item(out):
    return {'index': 0, 'output_json': json.dumps(out), 'cpu_seconds': 0.0, 'seconds': 0.0}


class BackwardCompatible(unittest.TestCase):
    def test_plain_words_score_as_bound_eval_2_on_campaign1_seed(self):
        fams = dev_sample()
        old, new = [], []
        for f in fams:
            out = sweep.certify(f)  # campaign-1 seed (control b16)
            old.append(E.score_family(f, {'status': 'ok'}, item(out)))
            new.append(B3.score_family(f, {'status': 'ok'}, item(out)))
            self.assertEqual((new[-1]['status'], new[-1]['gap'], new[-1]['valid']),
                             (old[-1]['status'], old[-1]['gap'], old[-1]['valid']), f['id'])
            self.assertEqual(new[-1].get('output_words'), old[-1].get('output_words'))
        self.assertEqual(E.aggregate(old)['combined_score'], E.aggregate(new)['combined_score'])
        self.assertGreater(sum(r['status'] == 'CERTIFIED' for r in new), 0)
        self.assertLess(sum(r['status'] == 'CERTIFIED' for r in new), len(new))

    def test_stored_campaign2_words_rescore_identically(self):
        if not ADA.exists():
            self.skipTest('campaign-2 result file absent')
        stored = json.loads(ADA.read_text())['result']['rows']
        by = {r['id']: r for r in stored}
        fams = dev_sample()
        for r in B3.rescore_stored(fams, stored):
            self.assertEqual((r['status'], r['gap']), (by[r['id']]['status'], by[r['id']]['gap']), r['id'])

    def test_plain_output_equals_explicit_unit_root_leaf(self):
        f = dev_sample()[3]
        out = sweep.certify(f)
        a = B3.score_output(f, out)
        b = B3.score_output(f, {'tree': {'words': out['words'], 'origins': [1] * f['k'], 'picks': [0] * f['k']}})
        self.assertEqual((a['status'], a['gap']), (b['status'], b['gap']))


class Contract(unittest.TestCase):
    def bad(self, out, k=2):
        with self.assertRaises(ValueError):
            K.parse_output(out, k)

    def test_limits(self):
        leaf = {'words': ['']}
        deep = leaf
        for _ in range(K.MAX_DEPTH + 1):
            deep = {'j': 0, 't': 1, 'le': leaf, 'ge': deep}
        self.bad({'tree': deep})
        self.bad({'tree': {'j': 0, 't': 13, 'le': leaf, 'ge': leaf}})
        self.bad({'tree': {'j': 2, 't': 1, 'le': leaf, 'ge': leaf}})
        self.bad({'tree': {'j': 0, 't': True, 'le': leaf, 'ge': leaf}})
        self.bad({'tree': {'words': ['X'], 'origins': [0, 1]}})
        self.bad({'tree': {'words': ['X'], 'origins': [2, 1], 'picks': [2, 0]}})
        self.bad({'tree': {'words': ['X'] * 33}})
        self.bad({'tree': {'words': ['X'], 'weights': ['1e1000000']}})
        K.parse_output({'tree': {'words': ['L' * 4000] * 32}}, 2)  # 128000 letters: fine in one leaf ...
        wide = {'words': ['L' * 4000] * 32}
        tree = {'j': 0, 't': 1, 'le': wide, 'ge': {'j': 0, 't': 2, 'le': wide, 'ge': wide}}
        self.bad({'tree': tree})  # ... but 384000 letters in the tree exceed the total cap
        full = leaf
        for _ in range(K.MAX_DEPTH):
            full = {'j': 0, 't': 1, 'le': full, 'ge': full}
        self.bad({'tree': full})  # depth 6 but 64 leaves

    def test_threshold_outside_box_and_origin_above_corner_invalid(self):
        f = REV84
        r = B3.score_output(f, {'tree': {'j': 0, 't': 2, 'le': {'j': 0, 't': 3, 'le': {'words': [W34]},
                                                                  'ge': {'words': [W34]}}, 'ge': {'words': [W34]}}})
        self.assertEqual(r['status'], 'INVALID_OUTPUT')
        r = B3.score_output(f, {'tree': {'j': 0, 't': 1, 'le': {'words': [W34]},
                                         'ge': {'words': [W52], 'origins': [3, 1]}}})
        self.assertEqual(r['status'], 'INVALID_OUTPUT')  # leaf [2, inf) with origin 3 > l = 2
        self.assertIn('exceeds lower corner', r['trace']['failure'])

    def test_unit_word_does_not_sort_refined_base(self):
        r = B3.score_output(REV84, {'tree': {'j': 0, 't': 2, 'le': {'words': [W34]},
                                             'ge': {'words': [W34], 'origins': [3, 1]}}})
        self.assertEqual(r['status'], 'INVALID_OUTPUT')
        self.assertIn('failed_word', r['trace'])


class Trees(unittest.TestCase):
    def test_group_m8_tree_certifies_and_audits(self):
        r = B3.score_output(REV84, GROUP)
        self.assertEqual((r['status'], r['n_leaves']), ('CERTIFIED', 3))
        self.assertEqual([x['box'] for x in r['leaves']], [[[1, 1], [1, 'inf']], [[2, 2], [1, 'inf']],
                                                           [[3, 'inf'], [1, 'inf']]])
        self.assertEqual(r['leaves'][2]['lhs'], '0')  # Bbar 54 = T(3,1) at the origin, as in the file
        self.assertTrue(r['leaves'][2]['given_weights_pass'])
        self.assertEqual(A.audit_claim(REV84, r['output'], r['certificate']), (True, 'ok'))
        bad = json.loads(json.dumps(r['certificate']))
        bad['leaves'][2]['weights'] = ['1', '0'] if len(bad['leaves'][2]['words']) == 2 else ['1']
        bad['leaves'][2]['words'] = [W52] + bad['leaves'][2]['words'][1:]
        self.assertFalse(A.audit_claim(REV84, r['output'], bad)[0])
        self.assertEqual(B3.score_output(REV84, {'words': [W34]})['status'], 'NO_CERTIFICATE')  # needs the tree

    def test_family_gap_is_max_leaf_gap(self):
        tree = {'j': 0, 't': 2, 'le': {'words': [W34]}, 'ge': {'words': [W34]}}
        r = B3.score_output(REV84, {'tree': tree})
        self.assertEqual([x['status'] for x in r['leaves']], ['CERTIFIED', 'NO_CERTIFICATE'])
        self.assertEqual(r['status'], 'NO_CERTIFICATE')
        self.assertEqual(r['gap'], '9')  # leaf [3, inf): lhs 34 + 2*12 - 54 = 4, slope 12: (4 - 1) + (12 - 6)

    def test_bounded_leaf_lp_matches_leaf_criterion(self):
        # one word, box [1, 3] x [1, inf): lhs = B - T + (12 - 6) * 2 on the bounded axis
        res = B3.leaf_lp([(34, [12, 0])], [(1, 3), (1, None)], 6, C.budget(8, 2))
        self.assertEqual((res['status'], res['gap']), ('NO_CERTIFICATE', 3))  # 34 - 42 + 12 = 4, gap 4 - 1
        res = B3.leaf_lp([(34, [12, 0])], [(1, 2), (1, None)], 6, C.budget(8, 2))
        self.assertEqual((res['status'], res['value']), ('CERTIFIED', -2))
        self.assertEqual(C.leaf_criterion([(1, 34, [12, 0], [1, 1])], [(1, 2), (1, None)], m=8)[3], -2)
        res = B3.leaf_lp([(34, [12, 7])], [(1, 2), (1, None)], 6, C.budget(8, 2))
        self.assertEqual((res['status'], res['gap']), ('NO_CERTIFICATE', 1))  # unbounded slope 7 > 6
        res = B3.leaf_lp([(43, [12, 0])], [(1, 3), (1, None)], 7, C.budget(9, 2))
        self.assertEqual((res['status'], res['gap']), ('BOUNDARY', 0))  # lhs exactly 1

    def test_box_points_literal(self):
        self.assertEqual(B3.box_points([(3, None), (1, 4)], [3, 1]), [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)])

    def test_revtree_control_certifies_m8_reversal(self):
        from integrations import bound3_control_revtree as R
        if R.table(8, 2) is None or R.table(8, 4) is None:
            self.skipTest('exact m=8 tables absent')
        out = json.loads(json.dumps(R.certify(REV84)))
        r = B3.score_output(REV84, out)
        self.assertEqual(r['status'], 'CERTIFIED')
        self.assertGreater(r['n_leaves'], 1)
        self.assertEqual(A.audit_claim(REV84, r['output'], r['certificate']), (True, 'ok'))


class Sandbox(unittest.TestCase):
    def test_tree_program_end_to_end(self):
        src = ('def certify(family):\n'
               '    k = family["k"]\n'
               '    leaf = {"words": [""], "origins": [1] * k}\n'
               '    return {"tree": {"j": 0, "t": 1, "le": leaf, "ge": leaf}}\n')
        fams = [make_family(list(range(1, 10)), 1 << 9), make_family([2, 1, 9, 8, 7, 6, 5, 4, 3], 4 | 64)]
        with tempfile.TemporaryDirectory() as d:
            prog = Path(d) / 'p.py'
            prog.write_text(src)
            res = B3.evaluate(prog, fams, require_os_sandbox=SANDBOX, jobs=1, cache_dir=Path(d) / 'c')
            self.assertEqual([r['status'] for r in res['results']], ['CERTIFIED', 'INVALID_OUTPUT'])
            self.assertEqual(res['evaluator_version'], 'bound-eval-3')
            self.assertEqual(A.audit_result(fams, res)['disagreements'], [])
            self.assertTrue(B3.evaluate(prog, fams, require_os_sandbox=SANDBOX, jobs=1,
                                        cache_dir=Path(d) / 'c')['cache_hit'])


if __name__ == '__main__':
    unittest.main()


class KillGroup(unittest.TestCase):
    def test_kill_group_swallows_eperm_and_esrch(self):
        from integrations import bound3_evaluator as B3

        class Proc:
            pid = 1  # signalling pid 1's group raises EPERM for a normal user

            def kill(self):
                raise ProcessLookupError

        B3._kill_group(Proc())  # must not raise
