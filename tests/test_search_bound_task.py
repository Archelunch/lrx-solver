"""Tests for the bound-m Track 2 task (autoresearch/bound-m-260925/TASK.md): families, the exact
evaluator, controls, the independent audit and the search-side plumbing. No provider calls."""
import argparse
import json
import os
from fractions import Fraction as Fr
from pathlib import Path
import random
import tempfile
import unittest

from integrations import bound_audit as A
from integrations import bound_backends as BB
from integrations import bound_control_naive as naive
from integrations import bound_control_sweep as sweep
from integrations import bound_control_sweeplp as sweeplp
from integrations import bound_evaluator as E
from integrations import lrx_m as C
from integrations.bound_task import SCHEMA, check_family, family_of_state, make_family
from integrations.lift_evaluator import gap_lp

ROOT = Path(__file__).resolve().parents[1]
BOUND = ROOT / 'autoresearch' / 'bound-m-260925'
LIFT = ROOT / 'autoresearch' / 'lift-m9-260924'
SANDBOX = os.environ.get('LRX_TEST_SANDBOX') == '1'


def item(out, cpu=0.0):
    return {'index': 0, 'output_json': json.dumps(out), 'cpu_seconds': cpu, 'seconds': cpu}


def score(fam, out):
    return E.score_family(fam, {'status': 'ok'}, item(out))


def write_set(directory, fams, name='development', screen=None):
    body = {'schema': SCHEMA, 'set': name, 'families': fams}
    if screen is not None:
        body['screen'] = screen
    path = Path(directory) / f'{name}.json'
    path.write_text(json.dumps(body))
    return path


class Families(unittest.TestCase):
    def test_construction_all_m_and_k(self):
        rng = random.Random(5)
        for m in (9, 10, 11):
            for k in range(1, m + 2):
                labels = rng.sample(range(1, m + 1), m)
                mask = sum(1 << g for g in rng.sample(range(m + 1), k))
                f = make_family(labels, mask)
                self.assertEqual((f['k'], f['slope_bound']), (k, m - 2))
                self.assertEqual(f['budget_unit'], m * (m + 1) // 2 + (k - 1) * (m - 2))
                self.assertEqual(len(f['unit_base']), m + k)
                self.assertEqual(check_family(f), f)
                self.assertEqual(family_of_state(f['unit_base']), (labels, mask, [1] * k))
        for m, a, b in ((9, 38, 7), (10, 47, 8), (11, 57, 9)):
            for k in (1, 5):
                self.assertEqual(make_family(list(range(1, m + 1)), (1 << k) - 1)['budget_unit'], a + b * k)
        with self.assertRaises(ValueError):
            make_family([1, 2, 3], 0)
        f = make_family(list(range(10, 0, -1)), 1234)
        self.assertEqual(f['id'], 'm10-mask1234-labels10.9.8.7.6.5.4.3.2.1')
        bad = dict(f, budget_unit=f['budget_unit'] + 1)
        with self.assertRaises(ValueError):
            check_family(bad)

    def test_frozen_sets_match_manifest(self):
        man = json.loads((BOUND / 'frozen' / 'manifest.json').read_text())
        import hashlib
        for name, digest in man['files'].items():
            self.assertEqual(hashlib.sha256((BOUND / 'frozen' / name).read_bytes()).hexdigest(), digest)
        dev = E.load_set(BOUND / 'frozen' / 'development.json')
        self.assertEqual((len(dev), {f['m'] for f in dev}), (303, {9, 10}))
        with self.assertRaises(ValueError):
            E.load_set(BOUND / 'frozen' / 'holdout.json')
        hold = E.load_set(BOUND / 'frozen' / 'holdout.json', allow_holdout=True)
        self.assertEqual(sum(f['m'] == 11 for f in hold), 165)
        keys = {(tuple(f['labels']), f['mask']) for f in dev}
        self.assertFalse(keys & {(tuple(f['labels']), f['mask']) for f in hold})
        raw = json.loads((BOUND / 'frozen' / 'development.json').read_text())
        self.assertEqual(len(raw['screen']), 30)
        self.assertEqual(sum(f['class'] == 'tight' for f in dev if f['m'] == 9), 7)


class Evaluator(unittest.TestCase):
    def test_root_family_certified_by_empty_word(self):
        f = make_family(list(range(1, 10)), 1 << 9)
        row = score(f, {'words': ['']})
        self.assertEqual(row['status'], 'CERTIFIED')
        self.assertEqual(row['lp']['base'], '0')
        self.assertIn('floor((-45) + 0*(r-k))', row['bound']['statement'])

    def test_wrap_swap_between_gap0_and_gapm_rejected(self):
        f = make_family(list(range(1, 10)), 1 | 1 << 9)
        self.assertEqual(f['unit_base'][0], 0)
        self.assertEqual(f['unit_base'][-1], 0)
        row = score(f, {'words': ['RX']})
        self.assertEqual(row['status'], 'INVALID_OUTPUT')
        self.assertEqual(row['trace']['failed_word']['first_bad_letter'], 1)
        self.assertEqual(row['gap'], '4000')

    def test_boundary_status_and_gap_zero(self):
        k, s, T = 2, 7, 52
        got = E.classify([(T + 1, [s, s]), (T + 5, [s - 1, s])], k, s, T, 9)
        self.assertEqual((got['status'], got['gap']), ('BOUNDARY', '0'))
        self.assertEqual(E.classify([(T, [s, s])], k, s, T, 9)['status'], 'CERTIFIED')
        self.assertEqual(E.classify([(T + 2, [s, s])], k, s, T, 9)['status'], 'NO_CERTIFICATE')
        cert = E.classify([(T - 3, [s + 1, 0]), (T - 3, [0, s + 1])], k, s, T, 9)
        self.assertEqual(cert['status'], 'CERTIFIED')  # the mixture is needed: neither word alone passes

    def test_gap_monotone_under_added_words(self):
        rng = random.Random(3)
        k, s, T = 3, 7, 52
        costs = [(rng.randrange(40, 70), [rng.randrange(0, 14) for _ in range(k)]) for _ in range(12)]
        gaps = [gap_lp(costs[:i], k, s, T + 1)[0] for i in range(1, len(costs) + 1)]
        self.assertTrue(all(a >= b for a, b in zip(gaps, gaps[1:])), gaps)

    def test_weights_checked_never_trusted(self):
        with self.assertRaises(ValueError):
            E.parse_output({'words': ['', ''], 'weights': [0.5, 0.5]})
        with self.assertRaises(ValueError):
            E.parse_output({'words': [''], 'weights': ['1/2']})
        f = make_family(list(range(1, 10)), 1 << 9)
        row = score(f, {'words': ['', 'LR'], 'weights': ['0', '1']})
        self.assertEqual(row['status'], 'CERTIFIED')
        fam = make_family(list(range(9, 0, -1)), 1 | 1 << 4)
        w = naive.certify(fam)['words'][0]
        row = score(fam, {'words': [w], 'weights': ['1']})
        self.assertEqual(row['status'], 'NO_CERTIFICATE')
        self.assertFalse(row['given_weights_pass'])

    def test_corrupted_and_wrong_family_words_rejected(self):
        fam = make_family([2, 1, 3, 4, 5, 6, 7, 8, 9], 1 << 9)
        good = naive.certify(fam)['words'][0]
        self.assertEqual(score(fam, {'words': [good]})['status'], 'CERTIFIED')
        self.assertEqual(score(fam, {'words': [good + 'X']})['status'], 'INVALID_OUTPUT')
        other = make_family([1, 3, 2, 4, 5, 6, 7, 8, 9], 1 << 9)
        row = score(other, {'words': [good]})
        self.assertEqual(row['status'], 'INVALID_OUTPUT')
        self.assertIn('final_prefix', row['trace']['failed_word'])
        for bad in ({'words': []}, {'words': ['Q']}, {'words': ['L'] * 33}, {'words': ['L' * 4001]}, []):
            self.assertEqual(score(fam, bad)['status'], 'INVALID_OUTPUT')

    def test_source_guard(self):
        self.assertIsNone(E.source_guard("W = 'LRX' * 30\n"))
        self.assertIn('L/R/X', E.source_guard("W = '" + 'LX' * 12 + "'\n"))
        self.assertIn('container', E.source_guard('T = [' + ','.join(['1'] * 65) + ']\n'))
        self.assertIn('bytes', E.source_guard('B = b"' + 'a' * 257 + '"\n'))
        for path in ('bound_control_naive.py', 'bound_control_sweep.py'):
            self.assertIsNone(E.source_guard((ROOT / 'integrations' / path).read_text()))
        with self.assertRaises(ValueError):
            BB.preflight_source("```python\nW = '" + 'L' * 30 + "'\ndef certify(f):\n    return {}\n```")

    def test_score_orders_certificates_first(self):
        def rows(cert, m, n):
            return [{'id': f'{m}-{i}', 'm': m, 'k': 2, 'status': 'CERTIFIED' if i < cert else 'NO_CERTIFICATE',
                     'valid': True, 'gap': '0' if i < cert else '9'} for i in range(n)]
        base = E.aggregate(rows(3, 9, 153) + rows(3, 10, 150))['combined_score']
        more = E.aggregate(rows(4, 9, 153) + rows(3, 10, 150))['combined_score']
        best_small = E.aggregate([dict(r, gap='0') for r in rows(3, 9, 153) + rows(3, 10, 150)])['combined_score']
        self.assertGreater(more - base, 0.2)
        self.assertLess(best_small - base, 0.15)
        self.assertEqual(E.per_example_metric({'status': 'CERTIFIED', 'valid': True, 'gap': '0'}), 1.0)
        self.assertEqual(E.per_example_metric({'status': 'NO_CERTIFICATE', 'valid': True, 'gap': '1'}), 0.25)

    def test_worker_end_to_end_process_isolation(self):
        fams = [make_family(list(range(1, 10)), 1 << 9), make_family([2, 1, 9, 8, 7, 6, 5, 4, 3], 4 | 64)]
        with tempfile.TemporaryDirectory() as d:
            prog = Path(d) / 'p.py'
            prog.write_text((ROOT / 'integrations' / 'bound_control_naive.py').read_text())
            res = E.evaluate(prog, fams, require_os_sandbox=SANDBOX, jobs=1, cache_dir=Path(d) / 'cache')
            self.assertEqual([r['status'] for r in res['results']], ['CERTIFIED', 'NO_CERTIFICATE'])
            self.assertTrue(E.evaluate(prog, fams, require_os_sandbox=SANDBOX, jobs=1,
                                       cache_dir=Path(d) / 'cache')['cache_hit'])
            slow = Path(d) / 'slow.py'
            slow.write_text('def certify(family):\n    while True:\n        pass\n')
            res = E.evaluate(slow, fams[:1], require_os_sandbox=SANDBOX, jobs=1, cache_dir=Path(d) / 'cache',
                             per_family=0.3, per_family_wall=1.0)
            self.assertEqual((res['results'][0]['status'], res['timeouts']), ('INCOMPLETE', 1))
            self.assertEqual(res['results'][0]['gap'], '4000')
            self.assertFalse(list((Path(d) / 'cache').glob('*.json'))[1:])  # only the first run was cached
            crash = Path(d) / 'crash.py'
            crash.write_text('def certify(family):\n    raise RuntimeError("no")\n')
            self.assertEqual(E.evaluate(crash, fams[:1], require_os_sandbox=SANDBOX, jobs=1)['results'][0]['status'],
                             'INCOMPLETE')
            table = Path(d) / 'table.py'
            table.write_text("W = '" + 'LX' * 20 + "'\ndef certify(family):\n    return {'words': [W]}\n")
            res = E.evaluate(table, fams, require_os_sandbox=SANDBOX, jobs=1)
            self.assertEqual({r['status'] for r in res['results']}, {'INVALID_OUTPUT'})


class Controls(unittest.TestCase):
    def test_sweep_pricing_matches_profile(self):
        rng = random.Random(7)
        for m in (9, 11):
            for k in (1, 4, m + 1):
                f = make_family(rng.sample(range(1, m + 1), m), sum(1 << g for g in rng.sample(range(m + 1), k)))
                for w, (B, beta) in list(sweep.pool(f['unit_base']).items())[:15]:
                    p = C.Profile(f['unit_base'], w)
                    self.assertEqual((p.base, list(p.beta)), (B, beta))

    def test_controls_certify_and_audit_agrees(self):
        dev = E.load_set(BOUND / 'frozen' / 'development.json')
        fams = [f for f in dev if f['class'] in ('easy', 'uniform')][:6] + [f for f in dev if f['class'] == 'tight'][:2]
        for mod in (naive, sweep, sweeplp):
            for f in fams:
                row = score(f, mod.certify(dict(f)))
                self.assertIn(row['status'], E.STATUSES)
                self.assertTrue(row['valid'])
                if row['status'] == 'CERTIFIED':
                    self.assertEqual(A.audit_claim(f, row['output_words'], row['certificate']), (True, 'ok'))
        f = make_family(list(range(1, 10)), 1 << 9)
        row = score(f, {'words': ['']})
        forged = dict(row['certificate'], base='-39')
        self.assertFalse(A.audit_claim(f, [''], forged)[0])
        self.assertFalse(A.audit_claim(f, ['L'], row['certificate'])[0])

    def test_lp_control_not_worse_than_b16(self):
        dev = E.load_set(BOUND / 'frozen' / 'development.json')
        for f in [x for x in dev if x['class'] == 'rev_rot'][:4]:
            a = score(f, sweep.certify(f))
            b = score(f, sweeplp.certify(f))
            self.assertLessEqual(Fr(b['gap']), Fr(a['gap']))
            self.assertGreaterEqual(b['status'] == 'CERTIFIED', a['status'] == 'CERTIFIED')


class PositiveControls(unittest.TestCase):
    def test_audited_m9_lift_certificates_are_certified(self):
        res = json.loads((LIFT / 'finalists' / 'holdout-results.json').read_text())['arms']['gepa']['results']
        raw = {}
        for line in (LIFT / 'finalists' / 'raw' / 'gepa-holdout.jsonl').read_text().splitlines():
            x = json.loads(line)
            raw[x['id']] = x
        done = 0
        for r in res:
            if r['status'] != 'CERTIFICATE' or done >= 25:
                continue
            _, mask, labels = r['child_id'].split('-')
            f = make_family([int(c) for c in labels[len('labels'):]], int(mask[len('mask'):]))
            words = raw[r['id']]['output']['words']
            self.assertEqual(score(f, {'words': words})['status'], 'CERTIFIED', r['child_id'])
            done += 1
        self.assertEqual(done, 25)

    def test_direct_mixture_m8_parents_certified_at_m8(self):
        inst = json.loads((LIFT / 'frozen' / 'development.json').read_text())
        inst = inst['instances'] if isinstance(inst, dict) else inst
        seen = set()
        for i in inst:
            p = i['parent']
            if p['id'] in seen or p['certificate']['kind'] != 'mixture' or len(seen) >= 30:
                continue
            seen.add(p['id'])
            f = make_family(p['labels'], p['mask'])
            self.assertEqual(f['slope_bound'], 6)
            row = score(f, {'words': [r['word'] for r in p['certificate']['rows']]})
            self.assertEqual(row['status'], 'CERTIFIED', p['id'])
        self.assertEqual(len(seen), 30)


class Backends(unittest.TestCase):
    def fake_result(self, n=6):
        fams = [make_family([2, 1, 9, 8, 7, 6, 5, 4, 3], sum(1 << g for g in gs), **{'class': c})
                for gs, c in (((2, 6), 'tight'), ((0, 4, 9), 'rev_rot'), ((1, 2, 3, 5), 'near_rev'),
                              ((3,), 'refl'), ((0, 9), 'uniform'), ((4, 5, 6, 7, 8, 9), 'easy'))][:n]
        rows = [score(f, sweep.certify(f)) for f in fams]
        return dict(E.aggregate(rows), results=rows), {f['id']: f for f in fams}

    def test_packet_limits_and_split(self):
        res, by_id = self.fake_result()
        text = BB.packet(res, by_id, 'screen none', 'screen', 'seed full development: m=9 1/1')
        self.assertLessEqual(len(text), BB.PACKET_MAX)
        self.assertTrue(text.startswith(BB.PACKET_MARK))
        self.assertIn('Mechanism', text)
        self.assertNotIn('m11-', text)
        a, b = BB.split_packet(text)
        self.assertLessEqual(len(a), BB.ARTIFACT_MAX)
        self.assertLessEqual(len(b), BB.ARTIFACT_MAX)
        self.assertEqual(len(BB.failing(res['results'])), min(3, sum(r['status'] != 'CERTIFIED' for r in res['results'])))

    def test_finalize_flags_m_literals(self):
        from integrations.bound_finalize import m_literals
        self.assertEqual(m_literals("if m == 9:\n    x = 1\nfor i in range(m):\n    pass\n"), ['if m == 9:'])
        self.assertEqual(m_literals((ROOT / 'integrations' / 'bound_control_sweep.py').read_text()), [])

    def test_preflight_last_fence_wins(self):
        src = BB.preflight_source("draft\n```python\ndef other():\n  pass\n```\nfinal\n```python\n"
                                  "def certify(family):\n    return {'words': ['']}\n```")
        self.assertIn('def certify', src)
        with self.assertRaises(ValueError):
            BB.preflight_source("```python\ndef certify(f):\n  pass\n```", "length")

    def test_sky_config_settings(self):
        with tempfile.TemporaryDirectory() as d:
            for engine in ('adaevolve', 'evox'):
                args = argparse.Namespace(iterations=40, model='m', broker_url='http://127.0.0.1:1/v1', max_tokens=8192,
                                          llm_timeout=10, reasoning_effort='low', engine=engine, eval_timeout=60,
                                          python=ROOT / '.venv-official' / 'bin' / 'python')
                if engine == 'adaevolve' and not args.python.exists():
                    continue
                c = BB.sky_config_dict(args, Path(d))
                self.assertEqual(c['search']['database']['random_seed'], BB.SKY_RANDOM_SEED)
                self.assertFalse(c['evaluator']['cascade_evaluation'])
                self.assertIs(c['evaluator']['inject_evaluator_context'], False)
                self.assertLessEqual(c['search']['num_context_programs'], 1)
                if engine == 'evox':
                    self.assertGreater(c['search']['switch_interval'], args.iterations)
                    self.assertIs(c['search']['database']['auto_generate_variation_operators'], False)
                else:
                    t = (Path(c['prompt']['template_dir']) / 'diff_user_message.txt').read_text()
                    self.assertNotIn('Example of valid diff format', t)
                    self.assertIn('SEARCH/REPLACE', t)

    def test_verifier_refuses_holdout_and_stages(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                BB.BoundVerifier(BOUND / 'frozen' / 'holdout.json', Path(d) / 'a', cache_dir=None, engine='t',
                                 provenance={}, max_requests=1)
            fams = [make_family(list(range(1, 10)), 1 << 9, **{'class': 'easy'}),
                    make_family([2, 1, 9, 8, 7, 6, 5, 4, 3], 4 | 64, **{'class': 'tight'})]
            path = write_set(d, fams, screen=[fams[1]['id']])
            v = BB.BoundVerifier(path, Path(d) / 'run', cache_dir=None, engine='t', provenance={}, max_requests=3,
                                 jobs=1, require_os_sandbox=SANDBOX)
            src = (ROOT / 'integrations' / 'bound_control_naive.py').read_text()
            out = v.evaluate(src)
            self.assertEqual((out['scope'], out['families']), ('screen', 1))
            self.assertEqual(out['full']['families'], 2)  # valid on the whole screen and first: full evaluation
            one = v.evaluate(src, fams[0]['id'])
            self.assertEqual(one['example_score'], 1.0)
            self.assertIn('per-family score', one['feedback'])
            v.evaluate(src)
            with self.assertRaises(PermissionError):
                v.evaluate(src)


class Hardening(unittest.TestCase):
    """Regression tests for the 2026-09-25 bound-task findings (one per finding)."""
    ROOT_FAM = make_family(list(range(1, 10)), 1 << 9)

    def test_weight_strings_bounded_before_fraction(self):
        import time
        start = time.process_time()
        for bad in ('1e10000000', '1e100000000', '1' * 41, '1/' + '2' * 41, '0.5', ' 1', '١'):
            with self.assertRaises(ValueError):
                E.parse_output({'words': ['X'], 'weights': [bad]})
        with self.assertRaises(ValueError):
            E.parse_output({'words': ['X'], 'weights': [10 ** 40]})
        self.assertLess(time.process_time() - start, 0.5)
        self.assertEqual(E.parse_output({'words': ['', 'L'], 'weights': ['1/2', '1/2']})[1], [Fr(1, 2)] * 2)
        self.assertEqual(E.parse_output({'words': ['', 'L'], 'weights': [1, 0]})[1], [1, 0])
        row = score(self.ROOT_FAM, {'words': [''], 'weights': ['1e10000000']})
        self.assertEqual(row['status'], 'INVALID_OUTPUT')
        self.assertIn('40 digits', row['trace']['failure'])

    def test_parent_cpu_measurement_defeats_self_reporting(self):
        self.assertIsNone(E.cpu_check(0.5, [{'cpu_seconds': 0.4}], 1))
        self.assertIn('allowance', E.cpu_check(8.0, [{'cpu_seconds': 0.1}] * 4, 4))
        self.assertIn('batch cap', E.cpu_check(15.0, [{'cpu_seconds': 3.0}] * 4, 4))
        self.assertIn('allowance', E.cpu_check(3.0, [{'cpu_seconds': -5.0}, {'cpu_seconds': 'x'}, None], 3))
        self.assertIn('allowance', E.cpu_check(8.0, [{'cpu_seconds': float('inf')}, {'cpu_seconds': 0.1}], 2))
        self.assertEqual(E.BATCH, 1)
        liar = ("import json, os, signal, time\n"
                "def certify(family):\n"
                "    signal.setitimer(signal.ITIMER_PROF, 0)\n"
                "    signal.setitimer(signal.ITIMER_REAL, 0)\n"
                "    t = time.process_time()\n"
                "    while time.process_time() - t < 0.75:\n"
                "        pass\n"
                "    n = len(json.load(open('case.json'))['families'])\n"
                "    for i in range(n):\n"
                "        with open('out-%04d.json' % i, 'w') as f:\n"
                "            f.write(json.dumps({'index': i, 'output_json': json.dumps({'words': ['']}),\n"
                "                                'cpu_seconds': 0.01, 'seconds': 0.01}))\n"
                "    os._exit(0)\n")
        from unittest import mock
        with tempfile.TemporaryDirectory() as d, mock.patch.multiple(E, IMPORT_CPU=0.2, STARTUP_CPU=0.3):
            prog = Path(d) / 'liar.py'
            prog.write_text(liar)
            res = E.evaluate(prog, [self.ROOT_FAM], require_os_sandbox=SANDBOX, jobs=1, per_family=0.3,
                             per_family_wall=1.0)
            row = res['results'][0]
            self.assertEqual((row['status'], row.get('timeout'), res['timeouts']), ('INCOMPLETE', True, 1))
            self.assertIn('parent-measured', row['trace']['failure'])
            honest = Path(d) / 'honest.py'
            honest.write_text((ROOT / 'integrations' / 'bound_control_naive.py').read_text())
            res = E.evaluate(honest, [self.ROOT_FAM], require_os_sandbox=SANDBOX, jobs=1, per_family=0.3,
                             per_family_wall=1.0)
            self.assertEqual(res['results'][0]['status'], 'CERTIFIED')

    def test_candidate_cannot_fork(self):
        src = ("import os\n"
               "def certify(family):\n"
               "    try:\n"
               "        pid = os.fork()\n"
               "    except OSError as exc:\n"
               "        return {'words': [''], 'note': 'fork denied'}\n"
               "    if pid == 0:\n"
               "        os._exit(0)\n"
               "    return {'words': ['Q']}\n")
        with tempfile.TemporaryDirectory() as d:
            prog = Path(d) / 'fork.py'
            prog.write_text(src)
            row = E.evaluate(prog, [self.ROOT_FAM], require_os_sandbox=SANDBOX, jobs=1)['results'][0]
            self.assertEqual((row['status'], row.get('note')), ('CERTIFIED', 'fork denied'))

    def test_source_guard_case_and_sentinel(self):
        self.assertIn('L/R/X-heavy', E.source_guard("W = '" + 'lx' * 2000 + "'.upper()\n"))
        self.assertIn('L/R/X-heavy', E.source_guard("W = '" + 'LX' * 2000 + "#'[:-1]\n"))
        self.assertIn('integer constant', E.source_guard('N = ' + '9' * 50 + '\n'))
        self.assertIn('outside docstrings', E.source_guard('S = ' + repr('ab' * 2100) + '\n'))
        self.assertIsNone(E.source_guard('"""' + 'a' * 5000 + '"""\ndef certify(f):\n    return {}\n'))

    def test_source_guard_chunked_tables(self):
        w = 'LX' * 40
        self.assertIn('concatenation', E.source_guard(
            'W = ' + ' + '.join(repr(w[i:i + 20]) for i in range(0, 80, 20)) + '\n'))
        self.assertIn('concatenation', E.source_guard("W = ''.join(" + repr([w[i:i + 20] for i in range(0, 80, 20)]) + ')\n'))
        spread = '\n'.join('W%d = %r' % (i, w[:20]) for i in range(30))
        self.assertIn('total', E.source_guard(spread + '\n'))
        dicts = ['d%d = {%s}' % (j, ', '.join("'f%d': %d" % (j * 60 + i, i) for i in range(60))) for j in range(5)]
        self.assertIn('constant elements', E.source_guard('\n'.join(dicts) + '\nT = {**d0, **d1, **d2, **d3, **d4}\n'))
        self.assertIsNone(E.source_guard("x = " + " + ".join(["'a'"] * 3000) + "\n"))  # no quadratic fold
        for path in ('bound_control_naive.py', 'bound_control_sweep.py', 'bound_control_sortprog.py'):
            self.assertIsNone(E.source_guard((ROOT / 'integrations' / path).read_text()))
        sortprog = BOUND / 'controls' / 'sortprog-gepa.py'
        if sortprog.exists():
            self.assertIsNone(E.source_guard(sortprog.read_text()))

    def test_no_os_sandbox_only_for_trusted_controls(self):
        with tempfile.TemporaryDirectory() as d:
            prog = Path(d) / 'bound_control_x.py'
            prog.write_text('def certify(family):\n    return {"words": [""]}\n')
            fams = write_set(d, [self.ROOT_FAM])
            for extra in ([], ['--holdout']):
                with self.assertRaises(SystemExit) as cm:
                    E.main(['--program', str(prog), '--families', str(fams), '--output', str(Path(d) / 'o.json'),
                            '--no-os-sandbox', *extra])
                self.assertIn('bound_control_', str(cm.exception))
            self.assertFalse((Path(d) / 'o.json').exists())

    def test_finalize_journal_records_each_arm_once(self):
        from integrations.bound_finalize import journaled
        calls = []

        def run(tag):
            calls.append(tag)
            return {'certified': len(calls)}
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / 'holdout-arms'
            self.assertEqual(journaled(j, 'a', 'sha', True, lambda: run('a')), {'certified': 1})
            self.assertEqual(journaled(j, 'a', 'sha', True, lambda: run('a2')), {'certified': 1})
            self.assertEqual(calls, ['a'])
            with self.assertRaises(SystemExit):
                journaled(j, 'a', 'other', True, lambda: run('a3'))
            (j / 'b.started').write_text('interrupted\n')
            with self.assertRaises(SystemExit):
                journaled(j, 'b', 'sha', True, lambda: run('b'))
            self.assertEqual(calls, ['a'])
            dev = Path(d) / 'development-arms'
            dev.mkdir()
            (dev / 'b.started').write_text('interrupted\n')
            self.assertEqual(journaled(dev, 'b', 'sha', False, lambda: run('b')), {'certified': 2})


if __name__ == '__main__':
    unittest.main()
