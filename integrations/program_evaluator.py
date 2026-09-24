"""Evaluate executable word proposers with trusted, exact family certificates.

Candidate Python runs in a separate Seatbelt process.  Only words cross the
boundary.  The parent replays and prices every word and reconstructs every
baseline profile before exact rational mixture verification.  A miss, crash,
or resource limit is never evidence of infeasibility.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

from integrations.mixture_lp import optimize
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile
from integrations.projected_mixtures import comparison, materialize, resources, state_for, verify_mixture
from src.lrx.certificates import replay_visible


ROOT = tuple(range(1, 9))
MAX_SOURCE_BYTES = 65536
MAX_WORDS_PER_CASE = 32
MAX_WORD_LENGTH = 4096
MAX_OUTPUT_BYTES = 262144


def _case(raw):
    if not isinstance(raw, dict):
        raise ValueError('case must be an object')
    labels = raw.get('labels')
    mask = raw.get('mask')
    if raw.get('m', 8) != 8 or not isinstance(labels, list) or any(type(x) is not int for x in labels) or sorted(labels) != list(ROOT):
        raise ValueError('case needs m=8 and a permutation of labels 1..8')
    if type(mask) is not int or not 1 <= mask < 512 or not 4 <= mask.bit_count() <= 7:
        raise ValueError('current evaluator scope is 4..7 retained zero blocks')
    if 'blocks' in raw and raw['blocks'] != mask.bit_count():
        raise ValueError('incorrect block count')
    key = raw.get('id') or f'mask{mask}-labels{"".join(map(str, labels))}'
    if not isinstance(key, str) or not key or len(key) > 160:
        raise ValueError('invalid case id')
    return {'id': key, 'm': 8, 'labels': labels, 'mask': mask, 'blocks': mask.bit_count()}


def _normalize_word(state, word):
    if type(word) is not str or not word or any(c not in 'LRX' for c in word):
        raise ValueError('word must be a nonempty L/R/X string')
    visible = list(state)
    kept = []
    for letter in word:
        if letter == 'X' and visible[0] == visible[1] == 0:
            continue
        kept.append(letter)
        if letter == 'L':
            visible = visible[1:] + visible[:1]
        elif letter == 'R':
            visible = visible[-1:] + visible[:-1]
        else:
            visible[0], visible[1] = visible[1], visible[0]
    reduced = []
    for letter in kept:
        if reduced and (reduced[-1], letter) in (('L', 'R'), ('R', 'L')):
            reduced.pop()
        else:
            reduced.append(letter)
    return ''.join(reduced)


def _direct_profile(state, word):
    word = _normalize_word(state, word)
    if replay_visible(state, word, max_steps=len(word)+1) != ROOT + (0,) * (len(state)-8):
        raise ValueError('word does not sort the unit-block state')
    info = resources(state, word)
    if info['base'] != len(word):
        raise ValueError('direct word price differs from materialized unit cost')
    return {'kind': 'direct', 'base': info['base'], 'gamma': info['beta'],
            'state': list(state), 'target': list(state), 'word': word,
            'affine': info['affine']}


def _direct_materialize(profile, lengths):
    """Literal zero-block lift for a direct word; upper bound uses triangle."""
    state = profile['state']
    zeros = iter(range(len(lengths)))
    atoms = [x if x else -(next(zeros)+1) for x in state]
    expanded = []
    for letter in profile['word']:
        if letter == 'L':
            atom = atoms[0]
            expanded.extend('L' * (1 if atom > 0 else lengths[-atom-1]))
            atoms = atoms[1:] + atoms[:1]
        elif letter == 'R':
            atom = atoms[-1]
            expanded.extend('R' * (1 if atom > 0 else lengths[-atom-1]))
            atoms = atoms[-1:] + atoms[:-1]
        else:
            left, right = atoms[:2]
            if left < 0 and right < 0:
                raise ValueError('zero-zero swap survived normalization')
            if left < 0:
                z = lengths[-left-1]-1
                expanded.extend('L'*z+'X'+'RX'*z)
            elif right < 0:
                z = lengths[-right-1]-1
                expanded.extend('X'+'LX'*z+'R'*z)
            else:
                expanded.append('X')
            atoms[0], atoms[1] = right, left
    reduced = []
    for letter in expanded:
        if reduced and (reduced[-1], letter) in (('L', 'R'), ('R', 'L')):
            reduced.pop()
        else:
            reduced.append(letter)
    initial = []
    z = 0
    for value in state:
        if value:
            initial.append(value)
        else:
            initial.extend([0] * lengths[z]); z += 1
    lifted = ''.join(reduced)
    upper = profile['base'] + sum(g*(ell-1) for g, ell in zip(profile['gamma'], lengths))
    if replay_visible(tuple(initial), lifted, max_steps=len(lifted)+1) != ROOT + (0,)*sum(lengths):
        raise ValueError('literal direct stretch replay failed')
    if len(lifted) > upper:
        raise ValueError('literal direct stretch exceeds recomputed upper bound')
    return {'length': len(lifted), 'upper': upper}


def _verified_baseline(case, rows):
    if not isinstance(rows, list):
        raise ValueError('baseline support must be a list')
    labels = case['labels']
    target = state_for(labels, case['mask'])
    out = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid baseline profile')
        state = tuple(row['state'])
        if len(state) != len(target) or sorted(state) != sorted(target) or tuple(row['target']) != target:
            raise ValueError('baseline state/target mismatch')
        word = row['word']
        if row.get('kind') == 'direct':
            if state != target:
                raise ValueError('direct baseline must start from family target')
            p = _direct_profile(state, word)
        else:
            cut = row['cut']
            if type(cut) is not int or not 0 <= cut < len(state):
                raise ValueError('invalid baseline cut')
            p = comparison(state, word, cut, labels)
            if p is None or not p['affine']:
                raise ValueError('invalid legacy comparison baseline')
        if p['base'] != row.get('base') or p['gamma'] != row.get('gamma'):
            raise ValueError('baseline asserted profile disagrees with trusted replay')
        if row.get('kind') == 'direct':
            out.append(p)
        else:
            # The comparison profile is a valid upper bound, but it can price
            # the materialized target word loosely.  Recompute a direct profile
            # so baseline and candidate words use identical actual costs.
            literal = materialize(p, [1] * case['blocks'])['word']
            direct = _direct_profile(target, literal)
            direct['origin'] = 'validated_legacy_comparison'
            out.append(direct)
    return out


def _certificate(profiles, result):
    if result.get('status') != 'CERTIFICATE':
        return None
    support = [{'profile': p, 'weight': w} for p, w in zip(profiles, result['weights']) if w != '0']
    bounds = verify_mixture([r['profile'] for r in support], [r['weight'] for r in support])
    for row in support:
        profile = row['profile']
        count = len(profile['gamma'])
        for lengths in ([1] * count, list(range(1, count + 1))):
            if profile.get('kind') == 'direct':
                _direct_materialize(profile, lengths)
            else:
                materialize(profile, lengths)
    return {'bounds': bounds, 'support': support,
            'scope': 'all positive lengths via direct word resources, triangle stretch bounds, and exact rational mixture; no comparison cut required'}


def _feasible_base(result, profiles):
    """Independently verify a returned feasible mixture before using its base."""
    if 'base' not in result or 'weights' not in result:
        return None
    weights = [Fraction(value) for value in result['weights']]
    if len(weights) != len(profiles) or any(weight < 0 for weight in weights) or sum(weights) != 1:
        raise ValueError('optimizer returned invalid primal weights')
    if not profiles or any(sum(weight * profile['gamma'][j]
                               for weight, profile in zip(weights, profiles)) > 6
                           for j in range(len(profiles[0]['gamma']))):
        raise ValueError('optimizer returned infeasible primal slopes')
    base = sum(weight * profile['base'] for weight, profile in zip(weights, profiles))
    if base != Fraction(result['base']):
        raise ValueError('optimizer returned inconsistent primal base')
    return base


def _mapping_hash(value):
    if value is None:
        return None
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _verified_dual(profiles, result, raw, blocks):
    """Check a proposed old-pool dual and primal witness using exact rationals."""
    if not isinstance(raw, dict):
        raise ValueError('dual must be an object')
    tight = raw.get('tight')
    mu = raw.get('mu')
    if not isinstance(tight, list) or not tight or any(type(j) is not int or not 0 <= j < blocks for j in tight) or len(set(tight)) != len(tight):
        raise ValueError('invalid dual tight positions')
    if not isinstance(mu, list) or len(mu) != len(tight):
        raise ValueError('dual multipliers must match tight positions')
    try:
        multipliers = [Fraction(x) for x in mu]
        intercept = Fraction(raw['nu'])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError('invalid rational dual') from exc
    if any(x < 0 for x in multipliers):
        raise ValueError('negative dual multiplier')
    base = _feasible_base(result, profiles)
    if base is None:
        raise ValueError('dual needs an exact feasible incumbent mixture')
    weights = [Fraction(x) for x in result['weights']]
    if len(weights) != len(profiles) or sum(weights) != 1 or any(x < 0 for x in weights):
        raise ValueError('invalid incumbent primal weights')
    slopes = [sum(w*p['gamma'][j] for w, p in zip(weights, profiles)) for j in range(blocks)]
    if any(slopes[j] != 6 for j in tight) or base != intercept - 6 * sum(multipliers):
        raise ValueError('incumbent primal and dual objective disagree')
    def reduced_cost(profile):
        return Fraction(profile['base']) + sum(x*profile['gamma'][j] for x, j in zip(multipliers, tight)) - intercept
    if any(reduced_cost(p) < 0 for p in profiles):
        raise ValueError('dual fails an incumbent column')
    if any(w and reduced_cost(p) != 0 for w, p in zip(weights, profiles)):
        raise ValueError('dual violates complementary slackness')
    return {'tight': tight, 'mu': multipliers, 'nu': intercept, 'reduced_cost': reduced_cost}


def _progress(accepted, before, before_profiles, after, after_profiles, dual, *, valid, rewardable, blocks):
    target = 31 + 6 * blocks
    base_before = _feasible_base(before, before_profiles)
    base_after = _feasible_base(after, after_profiles)
    entries = []
    if dual is not None:
        unique = set()
        for item in accepted:
            p = item['profile']
            key = (p['base'], tuple(p['gamma']))
            if key in unique:
                continue
            unique.add(key)
            cost = dual['reduced_cost'](p)
            entries.append({'word': p['word'], 'base': p['base'], 'gamma': p['gamma'],
                            'reduced_cost': str(cost)})
        entries.sort(key=lambda item: (Fraction(item['reduced_cost']), item['base'], item['word']))
    best_cost = Fraction(entries[0]['reduced_cost']) if entries else None
    improvement = max(Fraction(0), base_before - base_after) if valid and base_before is not None and base_after is not None else Fraction(0)
    negative = max(Fraction(0), -best_cost) if valid and best_cost is not None else Fraction(0)
    grade = ((improvement/(1+improvement) + negative/(1+negative)) / 2
             if rewardable else Fraction(0))
    return {'feasible_base_before': str(base_before) if base_before is not None else None,
            'feasible_base_after': str(base_after) if valid and base_after is not None else None,
            'strict_target': target,
            'strict_base_pass': bool(valid and base_after is not None and base_after < target),
            'base_deficit_after': str(max(Fraction(0), base_after-target)) if valid and base_after is not None else None,
            'base_improvement': str(improvement),
            'best_reduced_cost': str(best_cost) if valid and best_cost is not None else None,
            'negative_reduced_cost': str(negative),
            'best_useful_words': entries[:3] if valid else [],
            'secondary_grade': str(grade),
            'rewardable': rewardable,
            'diagnostic_scope': 'exact feasible mixtures and verified old-pool dual; negative reduced cost is necessary, not sufficient, for pool improvement'}


def _preexec(timeout):
    # This runs in the child immediately before exec, never in the verifier.
    cpu = max(1, int(timeout) + 1)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


class ProgramEvaluator:
    def __init__(self, cases, baseline=None, *, timeout_seconds=2.0,
                 max_source_bytes=MAX_SOURCE_BYTES, max_words_per_case=MAX_WORDS_PER_CASE,
                 max_word_length=MAX_WORD_LENGTH, require_os_sandbox=True,
                 incumbent=None, dual=None):
        self.cases = [_case(c) for c in cases]
        if len({c['id'] for c in self.cases}) != len(self.cases):
            raise ValueError('duplicate case ids')
        if not self.cases:
            raise ValueError('empty cases')
        baseline = baseline or {}
        if not isinstance(baseline, dict):
            raise ValueError('baseline must map case ids to profiles')
        self.reference_hashes = {'catalog': _mapping_hash(baseline),
                                 'incumbent': _mapping_hash(incumbent),
                                 'dual': _mapping_hash(dual)}
        self.baseline = {c['id']: _verified_baseline(c, baseline.get(c['id'], [])) for c in self.cases}
        if incumbent is not None and not isinstance(incumbent, dict):
            raise ValueError('incumbent must map case ids to direct profiles')
        if dual is not None and incumbent is None:
            raise ValueError('dual requires a frozen incumbent')
        if dual is not None and not isinstance(dual, dict):
            raise ValueError('dual must map case ids to exact witnesses')
        self.has_incumbent = incumbent is not None
        self.incumbent = {}
        self.dual = {}
        for case in self.cases:
            case_id = case['id']
            raw = (incumbent or {}).get(case_id, [])
            if not isinstance(raw, list) or any(not isinstance(row, dict) or row.get('kind') != 'direct' for row in raw):
                raise ValueError('incumbent supports must be direct profiles')
            self.incumbent[case_id] = _verified_baseline(case, raw)
            if dual is not None and case_id in dual:
                pool = self.baseline[case_id] + self.incumbent[case_id]
                self.dual[case_id] = _verified_dual(pool, optimize(pool), dual[case_id], case['blocks'])
        self.timeout_seconds = float(timeout_seconds)
        self.max_source_bytes = int(max_source_bytes)
        self.max_words_per_case = int(max_words_per_case)
        self.max_word_length = int(max_word_length)
        self.require_os_sandbox = bool(require_os_sandbox)
        if self.timeout_seconds <= 0 or min(self.max_source_bytes, self.max_words_per_case, self.max_word_length) <= 0:
            raise ValueError('resource caps must be positive')

    def _run_case(self, source_bytes, case):
        with tempfile.TemporaryDirectory(prefix='lrx-program-') as temp:
            scratch = Path(temp).resolve()
            candidate = scratch / 'candidate.py'
            worker = scratch / 'worker.py'
            input_file = scratch / 'case.json'
            output_file = scratch / 'output.json'
            profile_file = scratch / 'sandbox.sb'
            candidate.write_bytes(source_bytes)
            shutil.copyfile(Path(__file__).with_name('program_worker.py'), worker)
            input_file.write_text(json.dumps(case), encoding='utf-8')
            command = [sys.executable, '-I', '-S', str(worker), str(candidate), str(input_file), str(output_file)]
            isolation = 'process_only'
            if self.require_os_sandbox:
                # Python standard library is under sys.base_prefix.  Dyld and
                # the interpreter also need the immutable OS paths below.
                profile = sandbox_profile(read_paths=(sys.base_prefix, '/usr', '/System', '/Library', '/private/etc'),
                                          write_paths=(scratch,))
                profile_file.write_text(profile, encoding='utf-8')
                command = sandbox_command(command, profile_file)
                isolation = 'macos_seatbelt'
            env = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch), 'TMPDIR': str(scratch),
                   'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                   'LANG': 'C', 'LC_ALL': 'C'}
            start = time.monotonic()
            with (scratch/'stdout').open('wb') as stdout, (scratch/'stderr').open('wb') as stderr:
                proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL,
                                        stdout=stdout, stderr=stderr, start_new_session=True,
                                        preexec_fn=lambda: _preexec(self.timeout_seconds))
                try:
                    proc.wait(timeout=self.timeout_seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    return {'status': 'INCOMPLETE', 'reason': 'time limit', 'seconds': time.monotonic()-start,
                            'isolation': isolation}
                finally:
                    # A proposer can spawn descendants and return immediately.
                    # Keep them out of the next case and remove their scratch.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            log = (scratch/'stderr').read_bytes()[:4096].decode('utf-8', 'replace')
            if proc.returncode:
                if 'sandbox_apply: Operation not permitted' in log:
                    raise SandboxUnavailable('macOS Seatbelt denied by outer execution environment')
                return {'status': 'INCOMPLETE', 'reason': f'worker exit {proc.returncode}',
                        'stderr': log, 'seconds': time.monotonic()-start, 'isolation': isolation}
            if not output_file.exists() or output_file.stat().st_size > MAX_OUTPUT_BYTES:
                return {'status': 'INCOMPLETE', 'reason': 'missing or oversized worker output',
                        'seconds': time.monotonic()-start, 'isolation': isolation}
            try:
                payload = json.loads(output_file.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError):
                return {'status': 'INCOMPLETE', 'reason': 'invalid worker JSON',
                        'seconds': time.monotonic()-start, 'isolation': isolation}
            if not isinstance(payload, dict) or payload.get('status') not in ('ok', 'candidate_error'):
                return {'status': 'INVALID_OUTPUT', 'reason': 'worker JSON must be a status object',
                        'seconds': time.monotonic()-start, 'isolation': isolation}
            payload['seconds'] = time.monotonic()-start
            payload['isolation'] = isolation
            return payload

    def evaluate(self, program_path):
        source = Path(program_path)
        mode = source.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError('candidate source must be a regular, non-symlink file')
        if source.stat().st_size > self.max_source_bytes:
            raise ValueError('candidate source exceeds byte cap')
        with source.open('rb') as stream:
            raw = stream.read(self.max_source_bytes + 1)
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) > self.max_source_bytes:
            raise ValueError('candidate source exceeds byte cap')
        rows = []
        for case in self.cases:
            baseline_profiles = self.baseline[case['id']]
            baseline_result = optimize(baseline_profiles)
            baseline_certificate = _certificate(baseline_profiles, baseline_result)
            incumbent_profiles = baseline_profiles + self.incumbent[case['id']]
            incumbent_result = optimize(incumbent_profiles)
            incumbent_certificate = _certificate(incumbent_profiles, incumbent_result)
            attempt = self._run_case(raw, case)
            words = attempt.get('words')
            accepted, rejected = [], []
            if attempt.get('status') == 'ok':
                if not isinstance(words, list):
                    attempt = dict(attempt, status='INVALID_OUTPUT',
                                   reason=f'expected list of words; got {type(words).__name__}',
                                   actual_type=type(words).__name__)
                elif len(words) > self.max_words_per_case:
                    attempt = dict(attempt, status='INVALID_OUTPUT',
                                   reason=f'candidate returned {len(words)} words; limit {self.max_words_per_case}',
                                   actual_word_count=len(words), max_words_per_case=self.max_words_per_case)
                else:
                    state = state_for(case['labels'], case['mask'])
                    seen = set()
                    for index, word in enumerate(words):
                        try:
                            if type(word) is not str or len(word) > self.max_word_length:
                                raise ValueError('word has invalid type or exceeds length cap')
                            if word in seen:
                                continue
                            seen.add(word)
                            profile = _direct_profile(state, word)
                            accepted.append({'raw_word': word, 'normalized_word': profile['word'], 'profile': profile})
                        except (ValueError, TypeError, IndexError) as exc:
                            rejected.append({'index': index, 'reason': str(exc)[:200]})
            profiles = incumbent_profiles + [r['profile'] for r in accepted]
            candidate_result = optimize(profiles)
            result = candidate_result
            result_profiles = profiles
            # The incumbent is a valid feasible witness even if a numerical
            # basis proposal on the enlarged pool is worse or incomplete.
            incumbent_base = _feasible_base(incumbent_result, incumbent_profiles)
            candidate_base = _feasible_base(candidate_result, profiles)
            if incumbent_base is not None and (candidate_base is None or candidate_base > incumbent_base):
                result, result_profiles = incumbent_result, incumbent_profiles
            certificate = _certificate(result_profiles, result)
            if certificate is None and incumbent_certificate is not None:
                certificate = incumbent_certificate
            if attempt['status'] != 'ok':
                status = attempt['status']
            elif certificate is not None:
                status = 'CERTIFICATE'
            elif result['status'] == 'NO_CERTIFICATE':
                status = 'NO_CERTIFICATE'
            else:
                status = 'INCOMPLETE'
            progress = (_progress(accepted, incumbent_result, incumbent_profiles,
                                  result, result_profiles, self.dual.get(case['id']),
                                  valid=attempt['status'] == 'ok',
                                  rewardable=attempt['status'] == 'ok' and incumbent_certificate is None,
                                  blocks=case['blocks'])
                        if self.has_incumbent else None)
            rows.append({'case': case, 'status': status, 'candidate_run': {k:v for k,v in attempt.items() if k!='words'},
                         'accepted_words': accepted, 'rejected_words': rejected,
                         'lp': result, 'candidate_lp': candidate_result,
                         'incumbent_lp': incumbent_result if self.has_incumbent else None,
                         'baseline_lp': baseline_result,
                         'baseline_certified': baseline_certificate is not None,
                         'incumbent_certified': incumbent_certificate is not None,
                         'progress': progress, 'certificate': certificate})
        certified = sum(r['certificate'] is not None for r in rows)
        new = sum(r['certificate'] is not None and not r['baseline_certified'] for r in rows)
        incumbent_new = sum(r['certificate'] is not None and not r['incumbent_certified']
                            and r['candidate_run']['status'] == 'ok' for r in rows)
        invalid = sum(r['status'] in ('INVALID_OUTPUT', 'candidate_error', 'INCOMPLETE') for r in rows)
        secondary = (sum(Fraction(r['progress']['secondary_grade']) for r in rows) / len(rows)
                     if self.has_incumbent else Fraction(0))
        certificate_weight = max(1001, len(rows) + 2)
        score = (float(certificate_weight * incumbent_new - invalid + secondary) if self.has_incumbent
                 else float(1000 * new + certified - invalid))
        return {'kind': 'executable_program', 'candidate_hash': digest, 'combined_score': score,
                'certified': certified, 'new_certified': new, 'new_vs_catalog': new,
                'incumbent_certified': sum(r['incumbent_certified'] for r in rows),
                'new_vs_incumbent': incumbent_new,
                'secondary_score': str(secondary),
                'certificate_weight': certificate_weight if self.has_incumbent else 1000,
                'score_reference': 'frozen_incumbent' if self.has_incumbent else 'fixed_catalog',
                'reference_hashes': self.reference_hashes,
                'total_families': len(rows),
                'feedback': f'{incumbent_new if self.has_incumbent else new} new exact family certificates versus {"incumbent" if self.has_incumbent else "catalog"}; {certified}/{len(rows)} total; {invalid} execution or format failures. Partial progress is diagnostic, not proof; misses do not prove infeasibility.',
                'families': rows, 'isolation': 'macos_seatbelt' if self.require_os_sandbox else 'process_only',
                'limitations': ['Finite selected families only; universal scope of each accepted mixture relies on the direct word triangle expansion criterion.']}


def evaluate(program_path, cases_path, output_dir, *, baseline_path=None, timeout_seconds=2.0,
             require_os_sandbox=True, incumbent_path=None, dual_path=None):
    """File-based adapter for GEPA/SkyDiscover; writes one detailed JSON artifact."""
    cases_data = json.loads(Path(cases_path).read_text(encoding='utf-8'))
    cases = cases_data['cases'] if isinstance(cases_data, dict) else cases_data
    baseline = json.loads(Path(baseline_path).read_text(encoding='utf-8')) if baseline_path else None
    incumbent = json.loads(Path(incumbent_path).read_text(encoding='utf-8')) if incumbent_path else None
    dual = json.loads(Path(dual_path).read_text(encoding='utf-8')) if dual_path else None
    evaluator = ProgramEvaluator(cases, baseline, timeout_seconds=timeout_seconds,
                                 require_os_sandbox=require_os_sandbox,
                                 incumbent=incumbent, dual=dual)
    result = evaluator.evaluate(program_path)
    result['reference_files'] = {
        'catalog_sha256': hashlib.sha256(Path(baseline_path).read_bytes()).hexdigest() if baseline_path else None,
        'incumbent_sha256': hashlib.sha256(Path(incumbent_path).read_bytes()).hexdigest() if incumbent_path else None,
        'dual_sha256': hashlib.sha256(Path(dual_path).read_bytes()).hexdigest() if dual_path else None,
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / (result['candidate_hash'][:16] + '-evaluation.json')
    artifact.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    result['artifacts'] = {'evaluation': str(artifact.resolve())}
    return result
