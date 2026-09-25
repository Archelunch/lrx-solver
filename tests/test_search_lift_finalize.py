"""Fast test of the post-campaign finalize on a tiny fake campaign (no live data)."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from integrations import lift_finalize as F
from integrations import lift_task as T
from tests.test_search_lift_eval import CONTROL, parent

SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class LiftFinalizeTest(unittest.TestCase):
    def test_freeze_holdout_once_audit_report(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d)
            frozen = camp / 'frozen'
            frozen.mkdir()
            insts = T.build_instances(parent())
            (frozen / 'development.json').write_text(json.dumps({'instances': insts[:3]}))
            (frozen / 'holdout.json').write_text(json.dumps({'instances': insts[3:6]}))
            (frozen / 'manifest.json').write_text(json.dumps({'files': {
                'development.json': sha(frozen / 'development.json'), 'holdout.json': sha(frozen / 'holdout.json')}}))
            arm = camp / 'live-gepa-1'
            (arm / 'verified').mkdir(parents=True)
            shutil.copyfile(CONTROL, arm / 'verified' / 'best.py')
            (arm / 'manifest.json').write_text(json.dumps({
                'engine': 'gepa', 'status': 'COMPLETE', 'verified_best_hash': sha(CONTROL), 'seed_sha256': 'x',
                'verified_best_full': {'certificates': 0, 'instances': 3, 'gap_sum': '1'},
                'evaluation_trace': [], 'mechanism_evidence': {'candidate_sha256': ['a', 'b']}}))
            argv = ['--run-dir', str(camp), '--jobs', '2'] + ([] if SANDBOX else ['--no-os-sandbox'])
            F.main(argv)
            out = camp / 'finalists'
            hold = json.loads((out / 'holdout-results.json').read_text())
            self.assertTrue(hold['evaluated_once'])
            self.assertEqual(set(hold['arms']), {'gepa', 'naive-control'})
            report = (out / 'REPORT.md').read_text()
            for heading in ('## Arms', '## Independent audit', '## Success levels', '## Limitations'):
                self.assertIn(heading, report)
            stamp = (out / 'holdout-results.json').stat().st_mtime_ns
            F.main(argv)  # second call reuses the single holdout evaluation
            self.assertEqual(stamp, (out / 'holdout-results.json').stat().st_mtime_ns)
            (arm / 'verified' / 'best.py').write_text("def lift(instance):\n    return {'words': ['X']}\n")
            m = json.loads((arm / 'manifest.json').read_text())
            m['verified_best_hash'] = sha(arm / 'verified' / 'best.py')
            (arm / 'manifest.json').write_text(json.dumps(m))
            with self.assertRaises(SystemExit):  # frozen finalists differ
                F.main(argv)
            (frozen / 'holdout.json').write_text(json.dumps({'instances': insts[6:8]}))
            with self.assertRaises(SystemExit):  # holdout hash differs from the frozen manifest
                F.main(argv)


if __name__ == '__main__':
    unittest.main()
