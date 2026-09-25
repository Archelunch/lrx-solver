"""Tests for integrations/sort_finalize.py and sort_audit.py on the offline smoke runs.

The campaign directory is a throwaway copy under a temp dir: the smoke arms'
manifests and verified best sources, a small (4,2) development/holdout pair and
a frozen manifest naming the locked (4,2) table. The real holdout is never read.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from integrations import sort_audit as A
from integrations import sort_finalize as F
from integrations.sort_evaluator import SCHEMA, _sha
from src.lrx.table_bfs import DistanceTable

ROOT = Path(__file__).resolve().parents[1]
SORT = ROOT / 'autoresearch' / 'sort-m9-260925'
GEN = ROOT / 'datasets' / 'generated'


def build_camp(d):
    camp = Path(d) / 'camp'
    for arm in ('gepa', 'sequential', 'adaevolve', 'evox'):
        src = SORT / f'smoke-{arm}'
        dst = camp / f'live-v2-{arm}-000000-000000'
        (dst / 'verified').mkdir(parents=True)
        shutil.copyfile(src / 'manifest.json', dst / 'manifest.json')
        shutil.copyfile(src / 'verified' / 'best.py', dst / 'verified' / 'best.py')
    t = DistanceTable(GEN, 4, 2)
    states = []
    for dist in range(1, t.radius + 1):
        for v in t.spread_at(dist, 2):
            code = t.ranker.rank(t.ranker.positions(v))
            states.append({'id': f'm4r2-{code}', 'm': 4, 'r': 2, 'v': list(v), 'd': dist, 'budget': 12})
    frozen = camp / 'frozen'
    frozen.mkdir()
    for name, part in (('development', states[0::2]), ('holdout', states[1::2])):
        (frozen / f'{name}.json').write_text(json.dumps({'schema': SCHEMA, 'set': name, 'states': part}))
    (frozen / 'manifest.json').write_text(json.dumps({
        'files': {x: _sha((frozen / x).read_bytes()) for x in ('development.json', 'holdout.json')},
        'tables': [{'m': 4, 'r': 2, 'path': 'datasets/generated/dist_m4_r2.bin',
                    'table_sha256': t.meta['table_sha256']}]}))
    (camp / 'broker-ledger-sort-v2.gepa.json').write_text(json.dumps(
        {'attempts': [{'charged_usd': 0.01, 'status': 'ok', 'receipt_path': ''}]}))
    return camp


class FinalizeTest(unittest.TestCase):
    @unittest.skipUnless((SORT / 'smoke-evox' / 'verified' / 'best.py').is_file(), 'smoke runs not present')
    def test_finalize_on_smoke_runs(self):
        with tempfile.TemporaryDirectory() as d:
            camp = build_camp(d)
            argv = ['--run-dir', str(camp), '--no-os-sandbox', '--jobs', '2']
            out = F._finalize(_args(argv))
            fin = camp / 'finalists'
            manifest = json.loads((fin / 'manifest.json').read_text())
            arms = [f['arm'] for f in manifest['finalists']]
            self.assertEqual(arms, ['adaevolve', 'evox', 'gepa', 'sequential', 'naive-control', 'sweep-control'])
            for n in ('development', 'holdout'):
                self.assertEqual({a: v[1] for a, v in out['audit'][n].items()}, {a: 0 for a in arms})
            hold = json.loads((fin / 'holdout-results.json').read_text())
            self.assertTrue(hold['evaluated_once'])
            self.assertEqual(hold['arms']['sweep-control']['within_budget'], hold['arms']['sweep-control']['states'])
            report = (fin / 'REPORT.md').read_text()
            for text in ('## Arms', '## Mechanism evidence', '## Independent audit', '## Success levels',
                         '**Operational:**', '**Mathematical:**', '**Comparative:**', '## Limitations',
                         'Holdout m4r2', '| gepa | 1 |'):
                self.assertIn(text, report)
            F._finalize(_args(argv))  # second call reuses the single holdout evaluation
            self.assertEqual(json.loads((fin / 'holdout-results.json').read_text())['evaluated_utc'],
                             hold['evaluated_utc'])
            m = json.loads((fin / 'manifest.json').read_text())
            m['finalists'][0]['source_sha256'] = '0' * 64
            (fin / 'manifest.json').write_text(json.dumps(m))
            with self.assertRaises(SystemExit):
                F._finalize(_args(argv))

    def test_holdout_hash_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as d:
            camp = build_camp(d)
            with (camp / 'frozen' / 'holdout.json').open('a') as fh:
                fh.write(' ')
            with self.assertRaises(SystemExit):
                F._finalize(_args(['--run-dir', str(camp), '--no-os-sandbox']))


class AuditTest(unittest.TestCase):
    state = {'id': 's', 'm': 4, 'r': 2, 'v': [2, 1, 3, 4, 0, 0], 'd': 1, 'budget': 12}

    def row(self, **kw):
        base = {'id': 's', 'valid': True, 'within': True, 'length': 1, 'excess': 0, 'budget': 12, 'word': 'X'}
        return dict(base, **kw)

    def test_check_row(self):
        self.assertIsNone(A.check_row(self.state, self.row(), 1))
        self.assertIn('frozen d', A.check_row(self.state, self.row(), 2))
        self.assertIn('valid claim', A.check_row(self.state, self.row(word='L'), 1))
        self.assertIn('excess', A.check_row(self.state, self.row(excess=3), 1))
        self.assertIn('within', A.check_row(self.state, self.row(within=False), 1))
        self.assertIsNone(A.check_row(self.state, self.row(word='L', valid=False, final=[1, 3, 4, 0, 0, 2]), 1))
        self.assertEqual(A.execute([1, 2, 3], 'LRX'), [2, 1, 3])

    def test_audit_refuses_wrong_table_hash(self):
        with self.assertRaises(ValueError):
            A.audit({'s': self.state}, {'x': [self.row()]}, {(4, 2): (GEN, '0' * 64)})


def add_mismatch_arm(camp, tamper_packet=False):
    """A FIRST_PROMPT_MISMATCH adaevolve arm whose live first prompt differs from the approved capture
    in the mode-guidance block only (or, with tamper_packet, also in one packet line)."""
    from integrations.lift_backends import messages_sha256
    src = SORT / 'smoke-v2-adaevolve'
    for d in camp.glob('live-v2-adaevolve-*'):
        shutil.rmtree(d)
    run = camp / 'live-v2-adaevolve-111111-111111'
    shutil.copytree(src / 'verified' / 'evaluations', run / 'verified' / 'evaluations')
    cap_src = next(p for p in sorted((SORT / 'first-prompt-capture-v2' / 'capture-adaevolve-a').glob('request-*.json'))
                   if messages_sha256(json.loads(p.read_text())['body']['messages']) ==
                   (SORT / 'first-prompt-adaevolve.sha256').read_text().split()[0])
    cap_dir = camp / 'first-prompt-capture-v2' / 'capture-adaevolve-a'
    cap_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cap_src, cap_dir / 'request-0001.json')
    shutil.copyfile(SORT / 'first-prompt-adaevolve.sha256', camp / 'first-prompt-adaevolve.sha256')
    (camp / 'broker-config.json').write_text(json.dumps({'ledger': 'x/broker-ledger-sort-v2.json'}))
    body = json.loads(cap_src.read_text())['body']
    live = json.loads(json.dumps(body['messages']))
    content = live[1]['content']
    assert F.MODE_LABELS[0] in content
    content = content.replace(F.MODE_LABELS[0], F.MODE_LABELS[1])
    if tamper_packet:
        content = content.replace('SORT_PACKET_V1', 'SORT_PACKET_V1 ', 1)
    live[1]['content'] = content
    rec = camp / 'broker-ledger-sort-v2.adaevolve.json.receipts'
    shutil.rmtree(rec, ignore_errors=True)
    rec.mkdir()
    (rec / 'attempt-0001.json').write_text(json.dumps({'request_payload': dict(body, messages=live)}))
    m = json.loads((src / 'manifest.json').read_text())
    m.update(status='FIRST_PROMPT_MISMATCH', research_status='FIRST_PROMPT_MISMATCH',
             first_solution_prompt_check={'actual_sha256': messages_sha256(live), 'matches': False})
    for k in ('verified_best_result', 'verified_best_hash', 'evaluation_trace'):
        m.pop(k, None)
    (run / 'manifest.json').write_text(json.dumps(m))
    return run


class PromptMismatchAdmissionTest(unittest.TestCase):
    @unittest.skipUnless((SORT / 'smoke-v2-adaevolve').is_dir() and (SORT / 'first-prompt-capture-v2').is_dir(),
                         'v2 smoke and capture runs not present')
    def test_mode_block_only_is_admitted_and_packet_change_is_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            camp = build_camp(d)
            for arm in ('gepa', 'sequential', 'adaevolve', 'evox'):
                old = camp / f'live-v2-{arm}-000000-000000'
                if arm == 'adaevolve':
                    shutil.rmtree(old)
            add_mismatch_arm(camp)
            F._finalize(_args(['--run-dir', str(camp), '--no-os-sandbox', '--jobs', '2']))
            man = json.loads((camp / 'finalists' / 'manifest.json').read_text())
            ada = next(f for f in man['details'] if f['arm'] == 'adaevolve')
            rec = ada['admitted_with_prompt_mismatch']
            self.assertIn('EXPLORATION GUIDANCE', rec['unified_diff'])
            self.assertNotEqual(rec['live_sha256'], rec['captured_sha256'])
            self.assertIn('**adaevolve** admitted despite FIRST_PROMPT_MISMATCH',
                          (camp / 'finalists' / 'REPORT.md').read_text())
        with tempfile.TemporaryDirectory() as d:
            camp = build_camp(d)
            shutil.rmtree(camp / 'live-v2-adaevolve-000000-000000')
            add_mismatch_arm(camp, tamper_packet=True)
            F._finalize(_args(['--run-dir', str(camp), '--no-os-sandbox', '--jobs', '2']))
            man = json.loads((camp / 'finalists' / 'manifest.json').read_text())
            self.assertNotIn('adaevolve', [f['arm'] for f in man['finalists']])
            self.assertIn('outside the mode-guidance block', man['excluded_prompt_mismatch']['live-v2-adaevolve-111111-111111'])

    def test_mode_only_difference_rules(self):
        base = [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'A\n' + F.MODE_LABELS[0] + '\nB'}]
        swap = [base[0], {'role': 'user', 'content': 'A\n' + F.MODE_LABELS[1] + '\nB'}]
        balanced = [base[0], {'role': 'user', 'content': 'A\n\nB'}]
        self.assertTrue(F.mode_only_difference(swap, base)[0])
        self.assertTrue(F.mode_only_difference(balanced, base)[0])
        self.assertFalse(F.mode_only_difference([{'role': 'system', 'content': 'T'}, swap[1]], base)[0])
        self.assertFalse(F.mode_only_difference([base[0], {'role': 'user', 'content': 'A\n' + F.MODE_LABELS[1] + '\nC'}],
                                                base)[0])
        self.assertFalse(F.mode_only_difference(base, base)[0])


def _args(argv):
    return F.parser().parse_args(argv)


if __name__ == '__main__':
    unittest.main()
