"""Fast offline tests for the lift engine wiring (integrations/lift_backends.py)."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from integrations import lift_backends as B
from integrations import lift_task as T
from tests.test_search_lift_eval import CONTROL, parent

SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'
LIFT = Path(__file__).resolve().parents[1] / 'autoresearch' / 'lift-m9-260924'


def fake_instances(n_parents):
    out = []
    for i in range(n_parents):
        p = dict(parent(), id='p%02d' % i)
        out.extend(T.build_instances(p)[:2])
    return out


class LiftBackendsTest(unittest.TestCase):
    def test_screen_is_deterministic_and_bounded(self):
        insts = fake_instances(30)
        a, b = B.screen_parents(insts), B.screen_parents(list(reversed(insts)))
        self.assertEqual(a, b)
        self.assertEqual(len(a), B.SCREEN_PARENTS)
        self.assertEqual(len(set(a)), len(a))
        self.assertEqual(B.screen_parents(insts[:6]), ['p00', 'p01', 'p02'])

    def test_preflight(self):
        good = "```python\ndef lift(instance):\n    return {'words': []}\n```"
        self.assertIn('def lift', B.preflight_source(good, 'stop'))
        for bad, finish in ((good, 'length'), ('text\n' + good, 'stop'),
                            ("```python\ndef propose_words(case):\n    return []\n```", 'stop')):
            with self.assertRaises((ValueError, SyntaxError)):
                B.preflight_source(bad, finish)

    def test_staged_verifier_and_packet(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            path = d / 'dev.json'
            path.write_text(json.dumps({'instances': T.build_instances(parent())[:4]}))
            v = B.LiftVerifier(path, d / 'run', cache_dir=d / 'cache', archive_path=d / 'a.sqlite',
                               engine='test', provenance={}, max_requests=3, jobs=1,
                               require_os_sandbox=SANDBOX)
            first = v.evaluate(CONTROL.read_text())
            self.assertEqual((first['scope'], first['valid'], first['full']['valid']), ('screen', 4, 4))
            self.assertTrue(first['feedback'].startswith(B.PACKET_MARK))
            self.assertLessEqual(len(first['feedback']), B.PACKET_MAX)
            self.assertIn('failed construction', first['feedback'])
            bad = v.evaluate("def lift(instance):\n    return {'words': ['L']}\n")
            self.assertEqual((bad['valid'], bad['full']), (0, None))  # invalid: no full evaluation
            self.assertIn('INVALID_OUTPUT', bad['feedback'])
            v.evaluate(CONTROL.read_text(), 'ex8')
            with self.assertRaises(PermissionError):
                v.evaluate(CONTROL.read_text())
            self.assertEqual(v.state['full_evaluations'], 1)

    def test_approval_refuses_without_matching_hash(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            shutil.copyfile(LIFT / 'broker-config.json', d / 'broker-config.json')
            shutil.copyfile(LIFT / 'campaign-config.json', d / 'campaign-config.json')
            bc, cc = d / 'broker-config.json', d / 'campaign-config.json'
            with self.assertRaises(SystemExit):
                B.check_approval(bc, cc)
            (d / 'payload-approved.sha256').write_text('0' * 64 + '\n')
            with self.assertRaises(SystemExit):
                B.check_approval(bc, cc)
            digest = B.approval_hash(bc, cc)
            (d / 'payload-approved.sha256').write_text(digest + '  approved\n')
            self.assertEqual(B.check_approval(bc, cc), digest)
            cfg = json.loads(cc.read_text())
            cfg['engines']['gepa']['iterations'] += 1  # any cap change voids the approval
            cc.write_text(json.dumps(cfg))
            with self.assertRaises(SystemExit):
                B.check_approval(bc, cc)

    def test_first_prompt_file_and_guard(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            messages = [{'role': 'user', 'content': 'prompt with LIFT_PACKET_V1'}]
            (d / 'cap').mkdir()
            (d / 'cap' / 'request-0001.json').write_text(json.dumps(
                {'role': 'gepa_reflection', 'body': {'model': 'm', 'messages': messages}}))
            digest = B.write_first_prompt(d / 'cap', d / 'first-prompt.md', d)
            self.assertEqual(digest, B.messages_sha256(messages))
            self.assertIn(digest, (d / 'first-prompt.sha256').read_text())
            self.assertIn('prompt with LIFT_PACKET_V1', (d / 'first-prompt.md').read_text())
            lm = B.LiftBrokerLM('http://127.0.0.1:9/v1', 'm', 10, None, 1, None)
            lm.receipts, lm.expected_first_sha256 = [], '0' * 64
            with self.assertRaises(B.ob.BrokerHalted):  # halts before any network request
                lm('prompt with LIFT_PACKET_V1')

    def test_holdout_is_refused(self):
        with self.assertRaises(ValueError):
            B._verify_inputs(LIFT / 'frozen' / 'holdout.json', LIFT / 'frozen' / 'manifest.json')


if __name__ == '__main__':
    unittest.main()
