"""Fast tests for the sort-m9 task plumbing (autoresearch/sort-m9-260925/TASK.md)."""
import argparse
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

from integrations import lift_backends as lb
from integrations import sort_backends as B
from integrations import sort_evaluator as E
from integrations import sort_control_naive as naive
from integrations import sort_control_sweep as sweep
from src.lrx.certificates import replay_visible
from src.lrx.table_bfs import DistanceTable

SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'
ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'datasets' / 'generated'


def small_states(k=12):
    """k states of the locked (4,2) table, spread over distance, with exact d."""
    t = DistanceTable(GEN, 4, 2)
    out = []
    for d in range(1, t.radius + 1):
        for v in t.spread_at(d, 1):
            out.append({'id': 'm4r2-%d' % t.ranker.rank(t.ranker.positions(v)), 'm': 4, 'r': 2, 'v': list(v),
                        'd': d, 'budget': E.budget(4, 2)})
    return out[:k], t


def write_set(directory, states, name='development'):
    path = Path(directory) / f'{name}.json'
    path.write_text(json.dumps({'schema': E.SCHEMA, 'set': name, 'states': states}))
    return path


def optimal(t, v):
    word, cur = '', tuple(v)
    while t.distance(cur):
        for ch in 'LRX':
            nxt = replay_visible(cur, ch)
            if t.distance(nxt) == t.distance(cur) - 1:
                word, cur = word + ch, nxt
                break
    return word


class ControlsTest(unittest.TestCase):
    def test_controls_sort_every_small_state_and_random_m9(self):
        t = DistanceTable(GEN, 4, 2)
        goal = (1, 2, 3, 4, 0, 0)
        for code in range(len(t.dist)):
            v = t.vector_at(code)
            for mod in (naive, sweep):
                self.assertEqual(replay_visible(v, mod.sort_word(list(v))), goal)
        rng = random.Random(7)
        for r in (1, 3, 5):
            for _ in range(4):
                v = list(range(1, 10)) + [0] * r
                rng.shuffle(v)
                for mod in (naive, sweep):
                    self.assertEqual(replay_visible(tuple(v), mod.sort_word(v)), tuple(range(1, 10)) + (0,) * r)

    def test_sweep_beats_naive_on_extremal_state(self):
        v = [2, 1, 0, 0, 9, 8, 7, 6, 5, 4, 3]  # d = T = 52 (outer-layer report)
        self.assertLessEqual(len(sweep.sort_word(v)), len(naive.sort_word(v)))


class ScoringTest(unittest.TestCase):
    state = {'id': 's', 'm': 4, 'r': 2, 'v': [2, 1, 3, 4, 0, 0], 'd': 1, 'budget': 12}

    def score(self, item, header=None):
        return E.score_state(self.state, header or {'status': 'ok'}, item)

    def test_statuses(self):
        self.assertEqual(self.score({'word': 'X', 'seconds': 0, 'cpu_seconds': 0})['status'], 'WITHIN_BUDGET')
        row = self.score({'word': 'X' + 'LR' * 6, 'seconds': 0, 'cpu_seconds': 0})
        self.assertEqual((row['status'], row['excess'], row['slack']), ('OVER_BUDGET', 12, -1))
        row = self.score({'word': 'L', 'seconds': 0, 'cpu_seconds': 0})
        self.assertEqual((row['status'], row['valid'], row['final']), ('NOT_SORTED', False, [1, 3, 4, 0, 0, 2]))
        self.assertEqual(self.score({'word': 'XQ', 'seconds': 0, 'cpu_seconds': 0})['status'], 'INVALID_OUTPUT')
        self.assertEqual(self.score({'word': 'X' * 1001, 'length': 1001, 'seconds': 0, 'cpu_seconds': 0})['status'], 'INVALID_OUTPUT')
        self.assertEqual(self.score({'error': 'TimeoutError: per-state time limit'})['status'], 'TIMEOUT')
        self.assertEqual(self.score({'word': 'X', 'seconds': 9.0})['status'], 'TIMEOUT')
        self.assertEqual(self.score({'error': 'ValueError: boom'})['status'], 'CANDIDATE_ERROR')
        self.assertEqual(self.score(None)['status'], 'INCOMPLETE')
        self.assertEqual(self.score({}, {'status': 'candidate_error', 'error': 'x'})['status'], 'CANDIDATE_ERROR')
        self.assertEqual(self.score({}, {'status': 'INCOMPLETE', 'reason': 'batch wall limit'})['status'],
                         'INCOMPLETE')

    def test_word_shorter_than_exact_distance_is_an_evaluator_bug(self):
        with self.assertRaises(AssertionError):
            E.score_state(dict(self.state, d=3), {'status': 'ok'}, {'word': 'X', 'seconds': 0, 'cpu_seconds': 0})

    def test_aggregate_formula(self):
        rows = [self.score({'word': 'X', 'seconds': 0, 'cpu_seconds': 0}), self.score({'word': 'X' + 'LR' * 6, 'seconds': 0, 'cpu_seconds': 0}),
                self.score({'word': 'L', 'seconds': 0, 'cpu_seconds': 0}), self.score({'word': 'XLR', 'seconds': 0, 'cpu_seconds': 0})]
        agg = E.aggregate(rows)
        self.assertEqual((agg['within_budget'], agg['valid'], agg['invalid']), (2, 3, 1))
        self.assertAlmostEqual(agg['mean_excess'], (0 + 12 + 2) / 3)
        self.assertAlmostEqual(agg['combined_score'], 2 / 4 + 0.5 * (2 / 4) + 0.25 / (1 + 14 / 3) - 1 / 4)
        other = dict(rows[0], r=3, m=4, within=False)  # a second r with rate 0 drives the uniformity term
        agg2 = E.aggregate(rows + [other])
        self.assertEqual((agg2['min_r_within_rate'], agg2['worst_r']), (0.0, 'm4r3'))
        self.assertEqual(E.aggregate([rows[2]])['combined_score'], -1.0)

    def test_budget_formula(self):
        self.assertEqual([E.budget(9, r) for r in range(1, 7)], [45, 52, 59, 66, 73, 80])
        self.assertEqual(E.budget(10, 3), 71)


class SetsAndEvaluateTest(unittest.TestCase):
    def test_holdout_guard_and_malformed(self):
        states, _ = small_states(3)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(len(E.load_set(write_set(d, states))), 3)
            hold = write_set(d, states, 'holdout')
            with self.assertRaises(ValueError):
                E.load_set(hold)
            with self.assertRaises(ValueError):
                E.guard_not_holdout(hold)
            self.assertEqual(len(E.load_set(hold, allow_holdout=True)), 3)
            bad = write_set(d, [dict(states[0], budget=99)])
            with self.assertRaises(ValueError):
                E.load_set(bad)

    def test_evaluate_process_only_naive_crash_and_timeout(self):
        states, _ = small_states(8)
        with tempfile.TemporaryDirectory() as d:
            res = E.evaluate(ROOT / 'integrations' / 'sort_control_naive.py', states, require_os_sandbox=False,
                             jobs=2, cache_dir=Path(d) / 'cache', batch=5)
            self.assertEqual((res['valid'], res['invalid'], res['cache_hit']), (8, 0, False))
            self.assertEqual(E.evaluate(ROOT / 'integrations' / 'sort_control_naive.py', states,
                                        require_os_sandbox=False, jobs=2, cache_dir=Path(d) / 'cache',
                                        batch=5)['cache_hit'], True)
            crash = Path(d) / 'crash.py'
            crash.write_text('def sort_word(v):\n    if v[0] == 0:\n        raise ValueError("no")\n    return "L"\n')
            res = E.evaluate(crash, states, require_os_sandbox=False, jobs=2)
            self.assertEqual(res['valid'], 0)
            self.assertTrue({r['status'] for r in res['results']} <= {'CANDIDATE_ERROR', 'NOT_SORTED'})
            slow = Path(d) / 'slow.py'
            slow.write_text('import time\ndef sort_word(v):\n    time.sleep(5)\n    return ""\n')
            res = E.evaluate(slow, states[:2], require_os_sandbox=False, jobs=1)
            self.assertEqual([r['status'] for r in res['results']], ['TIMEOUT', 'TIMEOUT'])
            burn = Path(d) / 'burn.py'  # CPU-bound and swallows the alarm: caught by the recorded CPU time
            burn.write_text('import time\ndef sort_word(v):\n    t = time.process_time()\n'
                            '    while time.process_time() - t < 0.3:\n        try:\n            pass\n'
                            '        except BaseException:\n            pass\n    return "X"\n')
            res = E.evaluate(burn, states[:3], require_os_sandbox=False, jobs=1)
            self.assertEqual({r['status'] for r in res['results']}, {'TIMEOUT'})
            missing = Path(d) / 'missing.py'
            missing.write_text('x = 1\n')
            res = E.evaluate(missing, states[:2], require_os_sandbox=False, jobs=1)
            self.assertEqual({r['status'] for r in res['results']}, {'CANDIDATE_ERROR'})

    @unittest.skipUnless(SANDBOX, 'set LRX_TEST_SANDBOX=1 to run the Seatbelt path')
    def test_evaluate_under_seatbelt(self):
        states, _ = small_states(4)
        res = E.evaluate(ROOT / 'integrations' / 'sort_control_sweep.py', states, jobs=2)
        self.assertEqual((res['valid'], res['isolation']), (4, 'macos_seatbelt'))

    def test_prefix_trace_on_exact_table(self):
        states, t = small_states(12)
        tables = E.Tables({(4, 2): (GEN / 'dist_m4_r2.bin', t.meta['table_sha256'])})
        s = states[-1]
        w = optimal(t, s['v'])
        self.assertEqual(len(w), s['d'])
        trace = tables.prefix_trace(s, w)
        self.assertIsNone(trace['first_off_shortest_path'])
        padded = 'XX' + w
        trace = tables.prefix_trace(s, padded)
        on_path = t.distance(replay_visible(tuple(s['v']), 'X')) == s['d'] - 1
        self.assertEqual(trace['first_off_shortest_path']['step'], 2 if on_path else 1)
        with self.assertRaises(ValueError):
            E.Tables({(4, 2): (GEN / 'dist_m4_r2.bin', '0' * 64)})


class BackendsTest(unittest.TestCase):
    def test_preflight(self):
        src = 'def sort_word(v):\n    return ""\n'
        self.assertEqual(B.preflight_source('prose\n```python\nx = 1\n```\nmore\n```python\n' + src + '```'), src)
        for bad, finish in (('```python\n' + src + '```', 'length'), ('no fence', None),
                            ('```python\ndef lift(i):\n    pass\n```', None)):
            with self.assertRaises(ValueError):
                B.preflight_source(bad, finish)

    def test_packet_size_marker_and_worst_order(self):
        states, _ = small_states(8)
        rows = [E.score_state(s, {'status': 'ok'}, {'word': naive.sort_word(s['v']), 'seconds': 0, 'cpu_seconds': 0}) for s in states]
        rows[0] = E.score_state(states[0], {'status': 'ok'}, {'word': 'L', 'seconds': 0, 'cpu_seconds': 0})
        res = E.aggregate(rows)
        res['results'] = rows
        text = B.packet(res, 'none', {s['id']: s for s in states})
        self.assertLessEqual(len(text), B.PACKET_MAX)
        self.assertTrue(text.startswith(B.PACKET_MARK))
        self.assertIn('NOT_SORTED', text.splitlines()[3])
        self.assertIn('K = 14,15,17,18,20', text)
        rows = rows * 40
        res = dict(E.aggregate(rows), results=rows)
        self.assertLessEqual(len(B.packet(res, 'none', {s['id']: s for s in states})), B.PACKET_MAX)

    def test_verifier_best_budget_and_holdout_refusal(self):
        states, _ = small_states(6)
        with tempfile.TemporaryDirectory() as d:
            dev = write_set(d, states)
            v = B.SortVerifier(dev, Path(d) / 'run', cache_dir=None, engine='t', provenance={}, max_requests=2,
                               jobs=2, require_os_sandbox=False)
            bad = v.evaluate('def sort_word(v):\n    return "L"\n')
            good = v.evaluate((ROOT / 'integrations' / 'sort_control_sweep.py').read_text())
            self.assertGreater(good['combined_score'], bad['combined_score'])
            self.assertEqual(v.state['best']['candidate_hash'], good['candidate_hash'])
            self.assertIn('best so far: combined %.4f' % good['combined_score'], good['feedback'])
            with self.assertRaises(PermissionError):
                v.evaluate('def sort_word(v):\n    return ""\n')
            with self.assertRaises(ValueError):
                B.SortVerifier(write_set(d, states, 'holdout'), Path(d) / 'run2', cache_dir=None, engine='t',
                               provenance={}, max_requests=1, require_os_sandbox=False)

    def test_research_status(self):
        seed = {'within_budget': 10, 'invalid': 0, 'mean_excess': 30.0}
        self.assertEqual(B._research_status(seed, dict(seed, within_budget=11), ['h']), 'MORE_WITHIN_BUDGET')
        self.assertEqual(B._research_status(seed, dict(seed, within_budget=11, invalid=1), ['h']), 'NO_GAIN')
        self.assertEqual(B._research_status(seed, dict(seed, mean_excess=20.0), ['h']), 'GRADED_PROGRESS')
        self.assertEqual(B._research_status(seed, seed, []), 'NO_VALID_PROPOSAL')
        self.assertEqual(B._research_status(seed, None, []), 'INCOMPLETE')

    def test_fixed_plumbing_is_reused(self):
        self.assertEqual(lb.reflection_minibatch_size([{'id': 'development'}]), 1)
        self.assertFalse(lb.evox_strategy_evolution_enabled(40, False))
        with tempfile.TemporaryDirectory() as d:
            args = argparse.Namespace(iterations=40, model='m', broker_url='http://127.0.0.1:1/v1', max_tokens=8192,
                                      llm_timeout=10, reasoning_effort='low', engine='evox', eval_timeout=900,
                                      offline_no_auto_variation=False, evox_switch_interval=2)
            config = json.loads(B._sky_config(args, Path(d)).read_text())
            self.assertEqual(config['prompt']['system_message'], B.SYSTEM)
            self.assertFalse(config['search']['database']['auto_generate_variation_operators'])

    def test_approval_hash_and_refusal(self):
        states, _ = small_states(3)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            dev = write_set(d, states)
            (d / 'manifest.json').write_text(json.dumps({'files': {'development.json': E._sha(dev.read_bytes())}}))
            bc = json.loads((ROOT / 'autoresearch' / 'sort-m9-260925' / 'broker-config.json').read_text())
            cc = json.loads((ROOT / 'autoresearch' / 'sort-m9-260925' / 'campaign-config.json').read_text())
            cc['frozen_manifest'] = str(d / 'manifest.json')
            (d / 'broker-config.json').write_text(json.dumps(bc))
            (d / 'campaign-config.json').write_text(json.dumps(cc))
            h1 = B.approval_hash(d / 'broker-config.json', d / 'campaign-config.json')
            self.assertEqual(h1, B.approval_hash(d / 'broker-config.json', d / 'campaign-config.json'))
            with self.assertRaises(SystemExit):
                B.check_approval(d / 'broker-config.json', d / 'campaign-config.json')
            (d / 'payload-approved.sha256').write_text(h1 + '\n')
            self.assertEqual(B.check_approval(d / 'broker-config.json', d / 'campaign-config.json'), h1)
            cc['engines']['gepa']['iterations'] = 61
            (d / 'campaign-config.json').write_text(json.dumps(cc))
            with self.assertRaises(SystemExit):
                B.check_approval(d / 'broker-config.json', d / 'campaign-config.json')

    def test_campaign_sub_caps_fit_the_pool(self):
        bc = json.loads((ROOT / 'autoresearch' / 'sort-m9-260925' / 'broker-config.json').read_text())
        cc = json.loads((ROOT / 'autoresearch' / 'sort-m9-260925' / 'campaign-config.json').read_text())
        caps = [a['max_requests'] for a in cc['engines'].values()]
        self.assertLessEqual(sum(caps), bc['max_requests'])
        self.assertLessEqual(sum(caps), 400)
        self.assertEqual({k: a['iterations'] for k, a in cc['engines'].items()},
                         {'gepa': 60, 'sequential': 60, 'adaevolve': 50, 'evox': 40})
        approved = ROOT / 'autoresearch' / 'sort-m9-260925' / 'payload-approved.sha256'
        if approved.exists():  # written only by the human approval step; it must match the live material
            self.assertEqual(approved.read_text().split()[0],
                             B.approval_hash(ROOT / 'autoresearch' / 'sort-m9-260925' / 'broker-config.json',
                                             ROOT / 'autoresearch' / 'sort-m9-260925' / 'campaign-config.json'))


class FirstPromptGuardTest(unittest.TestCase):
    CAP = ROOT / 'autoresearch' / 'sort-m9-260925' / 'first-prompt-capture-v2'

    def receipts_from_capture(self, d, arm):
        ledger = Path(d) / 'ledger.json'
        rec = Path(str(ledger) + '.receipts')
        rec.mkdir()
        for i, p in enumerate(sorted((self.CAP / f'capture-{arm}-a').glob('request-*.json')), 1):
            (rec / f'attempt-{i:04d}.json').write_text(json.dumps({'request_payload': json.loads(p.read_text())['body']}))
        return ledger

    def test_sequential_guard_semantics(self):
        msgs = [{'role': 'user', 'content': 'x'}]
        self.assertFalse(B.first_prompt_mismatch(msgs, None))
        self.assertFalse(B.first_prompt_mismatch(msgs, lb.messages_sha256(msgs)))
        self.assertTrue(B.first_prompt_mismatch(msgs, '0' * 64))
        self.assertFalse(B.is_solution_request([{'role': 'user', 'content': 'ping'}]))  # connectivity probe
        self.assertFalse(B.is_solution_request([{'role': 'user', 'content': 'sort_word variation operator'}]))
        self.assertTrue(B.is_solution_request([{'role': 'user', 'content': 'def sort_word(v):'}]))

    @unittest.skipUnless((CAP / 'capture-evox-a').is_dir(), 'first-prompt captures not present')
    def test_post_hoc_check_on_captured_receipts(self):
        for arm in ('adaevolve', 'evox'):
            expected = (ROOT / 'autoresearch' / 'sort-m9-260925' / f'first-prompt-{arm}.sha256').read_text().split()[0]
            with tempfile.TemporaryDirectory() as d:
                ledger = self.receipts_from_capture(d, arm)
                self.assertEqual(B.verify_first_solution_prompt(ledger, expected), (expected, True))
                self.assertEqual(B.verify_first_solution_prompt(ledger, '0' * 64)[1], False)
                self.assertIsNone(B.verify_first_solution_prompt(ledger, None))
                self.assertIsNone(B.verify_first_solution_prompt(Path(d) / 'missing.json', expected))

    def test_approval_material_covers_all_four_first_prompts(self):
        sort_dir = ROOT / 'autoresearch' / 'sort-m9-260925'
        material = B.approval_material(sort_dir / 'broker-config.json', sort_dir / 'campaign-config.json')
        for arm, key in (('gepa', 'first_prompt_sha256'), ('sequential', 'first_prompt_sequential_sha256'),
                         ('adaevolve', 'first_prompt_adaevolve_sha256'), ('evox', 'first_prompt_evox_sha256')):
            path = sort_dir / B.FIRST_PROMPT_FILES[arm]
            self.assertEqual(material[key], path.read_text().split()[0] if path.is_file() else None)


if __name__ == '__main__':
    unittest.main()
