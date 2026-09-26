"""Tests for the campaign-3 driver (integrations/bound_c3.py) and its seed. No provider calls, no ports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

from integrations import bound3_evaluator as B3
from integrations import bound_c3 as c3
from integrations.bound_evaluator import source_guard
from integrations.bound_finalize import m_literals
from integrations.bound_task import make_family

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / 'autoresearch' / 'bound-m-c3-260926'
SEED = CAMP / 'seed' / 'c3-seed.py'
REV94 = make_family([9, 8, 7, 6, 5, 4, 3, 2, 1], 1 | 16)  # development family m9-mask17 (table-fed control: 3 leaves)


def seed_module():
    spec = importlib.util.spec_from_file_location('c3_seed_under_test', SEED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Configs(unittest.TestCase):
    def test_seed_hash_guard_and_no_m_literals(self):
        cc, bc = c3.campaign(CAMP)
        src = SEED.read_bytes()
        self.assertEqual(hashlib.sha256(src).hexdigest(), cc['seed_sha256'])
        self.assertIsNone(source_guard(src.decode()))
        self.assertEqual(m_literals(src.decode()), [])
        self.assertLessEqual(len(src), 65536)

    def test_caps_and_fresh_ledger_prefix(self):
        cc, bc = c3.campaign(CAMP)
        self.assertEqual(bc['max_usd'], 15.0)
        self.assertEqual(c3.pool(bc), 360)
        self.assertEqual(sum(cc['engines'][a]['max_requests'] for a in c3.ARMS) * len(cc['seeds']), 360)
        self.assertIn('broker-ledger-bound-c3', bc['ledger'])
        approved = CAMP / 'payload-approved.sha256'
        if approved.exists():  # approved 2026-09-26; `check-approval` is the live gate, here only the format
            self.assertRegex(approved.read_text().split()[0], r'^[0-9a-f]{64}$')

    def test_sky_knobs_carry_the_tree_system_prompt(self):
        cc, bc = c3.campaign(CAMP)
        for arm in ('adaevolve', 'evox'):
            knobs = c3.engine_knobs(cc, bc, arm, 1)
            self.assertEqual(knobs['sky']['prompt']['system_message'], c3.SYSTEM)
            self.assertEqual(knobs['sky']['search']['database']['random_seed'], 1)
        self.assertIn("'tree'", c3.SYSTEM)

    def test_forbidden_ids_never_open_the_holdout(self):
        cc, _ = c3.campaign(CAMP)
        seen = []
        real = c3._load

        def spy(path):
            seen.append(str(path))
            return real(path)

        with mock.patch.object(c3, '_load', spy):
            ids = c3.forbidden_ids(cc)
        self.assertTrue(ids and all(i.startswith('m11-') for i in ids))
        self.assertFalse(any('holdout' in p for p in seen))


class Packet(unittest.TestCase):
    def test_tree_row_and_invalid_row(self):
        fam = dict(REV94, **{'class': 'tight'})
        good = B3.score_output(fam, {'words': ['L']})
        self.assertEqual(good['status'], 'INVALID_OUTPUT')
        row = dict(good, id=fam['id'], m=9, k=2, mask=fam['mask'], budget_unit=fam['budget_unit'],
                   slope_bound=fam['slope_bound'], **{'class': 'tight'})
        text = c3.packet_v3({'per_m': {}, 'combined_score': 0.0, 'results': [row]}, {fam['id']: fam}, 'none',
                            'screen')
        self.assertTrue(text.startswith(c3.PACKET_MARK))
        self.assertIn(fam['id'], text)
        self.assertLessEqual(len(text), c3.PACKET_MAX)

    def test_valid_miss_shows_worst_leaf(self):
        fam = dict(REV94, **{'class': 'tight'})
        out = seed_module().certify(json.loads(json.dumps(REV94)))
        row = dict(B3.score_output(fam, out), id=fam['id'], m=9, k=2, mask=fam['mask'],
                   budget_unit=fam['budget_unit'], slope_bound=fam['slope_bound'], **{'class': 'tight'})
        if row['status'] == 'CERTIFIED':
            self.skipTest('seed certifies this family')
        text = c3.packet_v3({'per_m': {}, 'combined_score': 0.0, 'results': [row]}, {fam['id']: fam}, 'none',
                            'screen')
        self.assertIn('worst leaf', text)
        self.assertIn('reversal orbit: yes', text)


class Seed(unittest.TestCase):
    def test_seed_output_on_m9_reversal_is_a_valid_tree(self):
        mod = seed_module()
        out = json.loads(json.dumps(mod.certify(json.loads(json.dumps(REV94)))))
        self.assertIn('tree', out)
        row = B3.score_output(REV94, out)
        self.assertTrue(row['valid'])
        self.assertIn(row['status'], ('CERTIFIED', 'BOUNDARY', 'NO_CERTIFICATE'))

    def test_price_with_picks_matches_lrx_m_profile(self):
        from integrations import lrx_m as C
        mod = seed_module()
        fam = make_family([4, 3, 2, 1, 6, 5], 1 | 8)
        origins = [1, 3]
        ref = mod._refine(fam['unit_base'], origins)
        picks = [0, 1]
        checked = 0
        for w in mod._sweep_words(ref, float('inf'))[:60]:
            ours = mod._price_picks(ref, w, picks)
            try:
                p = C.Profile(C.refine(fam['unit_base'], origins), w, picks)
            except C.CheckError:
                self.assertIsNone(ours)
                continue
            self.assertEqual(ours, (p.base, list(p.beta)))
            checked += 1
        self.assertGreater(checked, 0)


if __name__ == '__main__':
    unittest.main()
