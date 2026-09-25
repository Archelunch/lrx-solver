# Loop hygiene v3 — synthesis report (2026-09-25)

Scope: three parallel specs (Track 1 sort-m9 v3 loop, Track 2 bound-m evaluator, Track 3
lean-loop) were implemented, reviewed, and fixed in this repo. This report is the synthesis:
what each track built, what the review found, what the fixes did, current test/smoke state,
the current repo-verification output, and the live checks still to authorize. No commits were
made and no live provider calls were made anywhere in this pass. `python tools/orchestrator.py
trusted` is `ok` throughout (TRUSTED core untouched).

## Track 1 — sort-m9 v3 search loop (`integrations/sort_loop3.py`)

**Spec:** `autoresearch/loop-v3-260925/SPEC-track1.md`. New files only; `sort_backends.py`,
`lift_backends.py`, `official_backends.py`, `sort_evaluator.py`, `sort_worker.py` untouched, so
the v2 approval hash (`7626d6b0...a328`) stays reproducible and TRUSTED stays locked. v3 adds a
GEPA arm (instance-level Pareto, 30 frozen instances, minibatch 3), a SkyDiscover Pareto+cascade
arm, a sequential control, and EvoX with strategy evolution forced off, all against the reused
sort-m9-260925 frozen development set and holdout, seeds [1,2,3].

**Files:** `integrations/sort_loop3.py`, `integrations/sort_loop3_finalize.py`,
`tests/test_search_loop_v3.py`, `tests/test_search_loop_v3_regressions.py`,
`autoresearch/sort-m9-v3-260925/{build_instances.py, campaign-config.json, broker-config.json,
broker-config-reflection.json, mock_api.py, run-one.sh, run-campaign.sh, run-smokes.sh,
run-captures.sh, approval-material.json, frozen-v3/*, first-prompt-*.{md,sha256} for gepa/
sequential/adaevolve/evox x seeds 1-3 plus gepa/sequential diagnosis hashes, smoke-*/ and
smoke-fix3-*/ capture and probe runs}`.

**Findings from review, both fixed:**
1. **High — GEPA never picked an improved child.** `evaluate_instances` only appended a "full"
   row when one request named all 30 instances; GEPA's cached-evaluation flow never sends such a
   request for an accepted child, so `best_full()` always fell back to the seed
   (`research_status` stuck at `NO_GAIN`). Fix: the verifier now tracks per-candidate instance
   coverage and appends one aggregated "full" row once the union of requests for a digest covers
   all 30 instances, whatever the request pattern. Confirmed by `smoke-fix3-gepa-s1-accept`,
   which reaches `research_status: MORE_WITHIN_BUDGET` (a real accepted, improved candidate), and
   by the new regression test `test_real_gepa_picks_the_improved_child`, which drives the pinned
   GEPA `optimize_anything` end to end through `_gepa_worker_v3` against the real
   `SortVerifierV3` with an LM stub that proposes a strictly better program.
2. **Medium — reveal cap spent on packets never shown, and revealed_ids overstated exposure.**
   Root cause was a wrong assumption that GEPA reflection sees only the minibatch's own
   `side_info`; with `cache_evaluation=True` the adapter cache actually hands reflection whatever
   `side_info` came from the request that last evaluated the parent, which could be a Withheld
   valset packet or a leftover remainder request. Fix: `cache_evaluation` is now off for GEPA (no
   extra metric-call cost, since the verifier's own result cache absorbs re-evaluation of the
   parent's minibatch), instance packets reveal optimal words only for a request of at most
   `reveal_minibatch` instances on a candidate already evaluated on them (i.e. exactly the parent
   re-evaluation), seed/final evaluations use `Withhold` (except the sequential arm's seed
   packet, which is that arm's first prompt), and reveals are granted tentatively and committed
   only for blocks that survive the packet size caps.
3. **Medium — ledger stats always read 0.** `sort_loop3_finalize.ledger_stats` looked for
   `{stem}.{arm}.s{seed}.json` while `_live_v3` writes `{stem}.{arm}-s{seed}.json` (`.` vs `-`).
   Fix: a single `ledger_paths(camp, engine, seed)` helper is now the one source of ledger
   naming; `_live_v3` writes `ledger`/`reflection_ledger` paths into the run manifest, and
   `ledger_stats` reads the manifest first and falls back to `ledger_paths`; a genuinely missing
   ledger reports `None`, not 0.

Because the reveal-policy fix changes what the GEPA prompt shows, the GEPA first-prompt and
diagnosis hashes for seeds 1-3 were regenerated (captured twice each through the mock; sequential/
AdaEvolve/EvoX hashes are unchanged and their smokes still match the old hashes). New approval
hash for the track's `approval-material.json`:
`8ec9bbe8e7d91b2a66d063a183c22222478e507ad6490703023890711e8cb5c7`
(sha256 of the JSON file as currently on disk; `payload-approved.sha256` was not written for this
track, matching the original implementation note). Superseded guard files and the prior
`approval-material.json` are preserved under
`autoresearch/sort-m9-v3-260925/superseded-fix3-260925/`.

**Tests:** `tests/test_search_loop_v3.py` (19 tests, all pass) +
`tests/test_search_loop_v3_regressions.py` (6 tests, all pass) — see full-suite run below; both
files run as part of `python -m unittest discover`.

**Smokes after the fix** (all offline, mock HTTP, under `autoresearch/sort-m9-v3-260925/`):
`smoke-fix3-gepa-s1` (3 iter, `COMPLETE`/`NO_GAIN`), `smoke-fix3-gepa-s1-accept` (3 iter,
`COMPLETE`/`MORE_WITHIN_BUDGET` — the accepted-child path), `smoke-fix3-gepa-s{1,2,3}-capture[2]`
(first-prompt recapture, `COMPLETE`/`NO_GAIN`), `smoke-fix3-sequential-s1`,
`smoke-fix3-adaevolve-s1`, `smoke-fix3-evox-s1` (3 iter each, `COMPLETE`/`NO_GAIN`, first-prompt
hashes unchanged from v3 pre-fix).

**Launch commands** (offline smoke, mirrors `run-one.sh`):
```
cd /Users/pavluhin/Documents/Projects/lrx-lab
python -m integrations.sort_loop3 smoke --arm gepa --seed 1 \
  --campaign-dir autoresearch/sort-m9-v3-260925 \
  --config autoresearch/sort-m9-v3-260925/campaign-config.json \
  --broker-config autoresearch/sort-m9-v3-260925/broker-config.json \
  --broker-config-reflection autoresearch/sort-m9-v3-260925/broker-config-reflection.json \
  --out autoresearch/sort-m9-v3-260925/smoke-fix3-gepa-s1
```
(arm in {gepa, sequential, adaevolve, evox}; live launch replaces `smoke` with `live` and needs
real broker endpoints, which are not authorized here.)

**Open issues / risks carried forward:**
- O1 from the spec (a fresh v3-only holdout vs. reuse of the v2 holdout) is still open; v3 still
  reuses the sort-m9-260925 holdout, so any v3 "holdout gain" is not independent of the v2 design
  process that touched that same holdout.
- `lb.evox_strategy_evolution_enabled` flips on at `iterations >= 100`; v3 still runs EvoX at 200
  iterations, so the "strategy evolution forced off with a post-run leak check" control must keep
  being exercised on every live run, not just smoke, since a live run is exactly the case that
  would hit the 200-iteration threshold in earnest.
- SkyDiscover `DatabaseConfig.random_seed` still defaults from OS entropy for pieces GEPA does not
  touch (AdaEvolve/EvoX parent selection); `engine_knobs()` pins it, so this is a config
  discipline item, not a code gap — worth a guard test that fails loud if a future edit drops the
  seed knob.
- Ledger fix removes the naming bug but still depends on `_live_v3` actually writing the manifest
  fields; no live run has exercised that path yet (only smoke, which the regression test
  `test_names_written_by_live_are_read` covers against a constructed manifest, not a live one).

## Track 2 — bound-m evaluator (`integrations/bound_evaluator.py`, `bound_worker.py`)

**Spec:** `autoresearch/bound-m-260925/SPEC-track2.md`.

**Findings from review, status after fix pass (verified by rerunning the full suite, see
below — `tests/test_search_bound_task.py` now contains dedicated regression tests for every
finding: `test_weight_strings_bounded_before_fraction`,
`test_parent_cpu_measurement_defeats_self_reporting`, `test_source_guard_chunked_tables`,
`test_source_guard_case_and_sentinel`, `test_no_os_sandbox_only_for_trusted_controls`,
`test_finalize_journal_records_each_arm_once`, `test_candidate_cannot_fork`, all passing):**
1. **Medium — unbounded `Fraction(x)` DoS.** Candidate weight strings went straight into
   `Fraction()` outside the sandbox with no size/format check; a huge-exponent string
   (`'1e10000000'`) stalled the trusted process for ~10 s per call, and larger exponents did not
   return in the time available. `test_weight_strings_bounded_before_fraction` now exercises the
   fix (a regex/length bound applied before `Fraction()` is ever called).
2. **Medium — the per-family CPU/wall cap was not actually enforced.** The parent trusted only
   candidate-reported `cpu_seconds`/`seconds`, which a candidate sharing the worker process could
   fake after disarming its own itimers and forking. `test_parent_cpu_measurement_defeats_self_reporting`
   now exercises the fix (parent-side `os.wait4`/rusage measurement, batch marked INCOMPLETE on
   disagreement).
3. **Low — the anti-table source guard was trivially chunk-bypassable** (string concatenation and
   `{**a,**b}` dict merges evaded the per-node literal caps). `test_source_guard_chunked_tables`
   now exercises the fix.
4. **Low — `source_guard` case-folding / sentinel-splitting bypass.**
   `test_source_guard_case_and_sentinel` now exercises the fix.
5. **Low — `--no-os-sandbox` was only gated together with `--holdout`.**
   `test_no_os_sandbox_only_for_trusted_controls` now exercises the fix (gate applies whenever
   `--no-os-sandbox` is passed, independent of `--holdout`).
6. **Low — holdout-evaluated-once guarantee did not survive a crash mid-loop.**
   `test_finalize_journal_records_each_arm_once` now exercises the fix (a per-arm journal is
   written as each arm finishes, and a rerun will not re-evaluate an arm the journal already
   covers).

**Tests:** `tests/test_search_bound_task.py`, 28 tests, all pass (see run below); includes a
dedicated `Hardening` test class for the above.

**Approval:** `autoresearch/bound-m-260925/approval-material.json` current sha256:
`e52d9b3a764fae7ab5ebfa36fd202cd13290eda0693eb58cd90959d3c696febc`.

**Smokes:** offline mock smokes present for all four arms plus a v2 set
(`smoke-{gepa,sequential,adaevolve,evox}` and `smoke-v2-*`), each with a `.console.log`; no
`smoke-summary.json` files are written by this track's smoke driver (differs from Track 1's
convention), so status is read from the console logs / verified-evaluation directories under each
smoke dir.

**Launch command** (offline smoke):
```
cd /Users/pavluhin/Documents/Projects/lrx-lab
bash autoresearch/bound-m-260925/run-smokes.sh
# or a single arm, mirroring run-gepa.sh / run-sequential.sh / run-adaevolve.sh / run-evox.sh
```

**Open issues / risks carried forward:**
- The CPU-measurement fix depends on `os.wait4` semantics that are POSIX/macOS-specific (matches
  the Seatbelt sandbox path already required here); no Linux CI path has been exercised for this.
- `bound_worker.py`'s sandbox profile still allows `process*`, so fork-based CPU laundering is now
  *detected* (parent measurement) rather than *prevented*; a future change to the profile to deny
  fork (`(deny process-fork)`) plus `RLIMIT_NPROC` is noted in the review but not yet applied —
  worth confirming this repo still wants detection-only or wants prevention too.

## Track 3 — lean-loop (`integrations/lean_evaluator.py`, `lean_task.py`, `lrxlean/Audit.lean`)

**Spec:** `autoresearch/lean-loop-260925/SPEC-track3.md`.

**Findings from review, status after fix pass (verified by rerunning the full suite —
`tests/test_search_lean_task.py` covers every finding, all passing):**
1. **High — helper-theorem credit A was gameable by lemma spam** (unused `have`s reachable from a
   `sorry`-stub root earned the same credit as real milestone progress).
   `test_lemma_spam_earns_no_helper_credit` now exercises the fix (reachability alone no longer
   suffices; credit requires reachability from a *closed* root and a real dependency on
   `LrxLean.Defs`).
2. **Medium — correct, kernel-checked proofs scored 0 (`audit_mismatch`) for layout reasons**
   (indented declaration, doc comment on the same line, name on the next line) because the
   footer's `#print axioms` emission depended on a column-0 regex.
   `test_footer_line_errors_are_kept_out_of_body_messages` and the broader `ContractTests`/
   `LeanIntegrationTests` classes (`test_correct_proof_closes_in_any_layout`) now exercise the
   fix.
3. **Low — lexical word ban hit ordinary English inside comments** (`prefix`, `postfix`,
   `initialize`, `end`, "Lean."). `test_comment_words_are_not_banned_but_code_and_hidden_code_are`
   now exercises the fix (comments are stripped before the word-ban check; the banned-word list
   is now fully documented in the prompt).
4. **Low — result cache keyed on a hand-bumped `VERSION` string, not evaluator code hash.**
   `test_key_binds_evaluator_source_and_sandbox` now exercises the fix.
5. **Low — cache key did not bind `require_sandbox`, a latent trust-boundary gap** (not
   exploitable end-to-end today since no wired call site passes `require_sandbox=False` against a
   shared cache dir, but flagged as real). `test_unsandboxed_and_no_verdict_results_are_never_cached`
   now exercises the fix.

**Tests:** `tests/test_search_lean_task.py`, 23 tests, all pass (see run below).

**Approval:** `autoresearch/lean-loop-260925/approval-material.json` current sha256:
`f62eb326880437d095e7e73690dd8f5f2d047da3ac5ad587dc6385422a3ac7d1`.

**Smokes:** `smoke-{gepa,sequential,adaevolve}` (pre-fix), `smoke-{gepa,sequential,adaevolve}-fix`
plus `-fix-capture` (post-fix first-prompt recapture), `smoke-{gepa-v2,gepa-v3}` and
`-repeat2/-repeat3` probes, each with mock jsonl + log. `smoke-finalize.json` /
`smoke-finalize-fix.json` hold the finalize-stage smoke output before/after the fix pass.

**Launch command** (offline smoke, mirrors `run-gepa.sh`):
```
cd /Users/pavluhin/Documents/Projects/lrx-lab
bash autoresearch/lean-loop-260925/run-gepa.sh   # or run-sequential.sh / run-adaevolve.sh
```

**Open issues / risks carried forward:**
- EvoX is intentionally excluded from this track (`test_engines_exclude_evox_and_sky_config_is_pinned`)
  per AGENTS.md's ban on LLM-written search-strategy code running live; confirm this stays true if
  the track is ever extended.
- The lexical-ban fix strips `--`/`/- -/` comments before checking; verify no adversarial nested
  block comment (`/- /- -/ -/`) reopens a bypass — not covered by a dedicated test in this pass.
- Helper-credit fix requires a dependency on `LrxLean.Defs`; a lemma that routes through an
  intermediate reachable-and-closed lemma that itself only touches `LrxLean.Defs` indirectly
  should be re-checked against the fix's exact reachability rule before trusting A at scale.

## Repository verification (rerun after all three fix passes, this session)

```
$ python -m unittest discover -s tests -p 'test_*.py' -v
...
Ran 567 tests in 43.341s

OK (skipped=4)
```

```
$ python -m compileall -q src tests
(no output; exit code 0)
```

```
$ python -m src.lrx.cli smoke
{"family": {"k": 3, "lower_bound_checked": false, "marks": [{"mark": 3, "projection": 12,
"terminal": true}, {"mark": 22, "projection": 12, "terminal": true}], "verified_upper_bound":
true, "word": "LLXRXRXRRRXLXLLL", "word_length": 16}, "passed": true, "visible_states": 12}
```

Additionally:
```
$ python tools/orchestrator.py trusted
{"ok": true, "changed": [], "missing_from_lock": []}

$ python -m integrations.sort_backends approval-hash
7626d6b04f62c72af7340f9b270b02c04bb9526d233b5347917fe00f20baa328   # unchanged from v2
```

All three tracks' offline test files (`test_search_loop_v3.py`, `test_search_loop_v3_regressions.py`,
`test_search_bound_task.py`, `test_search_lean_task.py`) are already picked up by `discover` and
included in the 567-test total above; they were also run standalone to confirm no cross-track
interaction:
```
$ python -m unittest tests.test_search_loop_v3 tests.test_search_loop_v3_regressions -v
Ran 25 tests ... OK
$ python -m unittest discover -s tests -p 'test_*bound*.py' -v
Ran 28 tests ... OK
$ python -m unittest discover -s tests -p 'test_*lean*.py' -v
Ran 23 tests ... OK
```

## Next live checks (not run — require explicit authorization per AGENTS.md; all offline/mock
so far)

These are the minimum live probes to validate each track's real-endpoint wiring before a full
campaign, with rough cost estimates based on the smoke evidence above (actual pricing depends on
the live broker's rates, which this session has no access to):

**(a) sort-m9-v3, one seed, one arm, 20 iterations.**
Recommend GEPA seed 1 (it exercises both brokers — flash + reflection — and is the arm the fix
pass most changed). Command: `--arm gepa --seed 1 --iterations 20` via `sort_loop3.py live`
against `autoresearch/sort-m9-v3-260925/{broker-config.json,broker-config-reflection.json}` with
real endpoints substituted. Cost driver: full-development evaluation (1500 states) took 9-23 s
median / 45 s max per candidate in the v2 live data quoted in the spec; GEPA's minibatch-3 +
occasional full-valset requests plus ~20 reflection calls (one per accepted-or-tried iteration,
each showing the ~2000-char packet) is the dominant token cost. Order-of-magnitude: 20-40 flash
calls (candidate generation) + ~15-20 reflection calls, each reflection prompt in the low
thousands of tokens per the packet caps (2500/instance, 6000 sequential, 300-state reveal cap) —
call it a few hundred thousand input tokens and a few dozen thousand output tokens total for the
run; get an exact quote from the live broker's cost report before launch (`ledger.json` after the
run gives the real figure, per the ledger-stats fix in Track 1).

**(b) bound-m, one arm, 20 iterations.**
Recommend `sequential` first (simplest control path, exercises the fixed CPU-measurement and
weight-string guards without GEPA's reflection overhead) via `run-sequential.sh` with
`--iterations 20` and real endpoints. Cost driver: per-family evaluation is capped at 3 s CPU / 5 s
wall (now actually enforced by the parent-side measurement fix), times up to 303 families per
candidate batch, but only failing/changed families need re-certification per candidate; expect
this to be cheaper per call than Track 1 (no 1500-state full evaluation) but with more candidates
needed since the score landscape is coarser (certificate count, not a continuous metric).

**(c) lean-loop, one arm, 10 iterations, target L1.**
Recommend `sequential` (per the spec's ranking of lowest-risk arm) via `run-sequential.sh` with
`--iterations 10 --target M1` — correction: the requested target is L1, so use whichever CLI flag
selects that milestone (`lean_task.py`'s milestone selector; confirm the exact flag name against
the pinned CLI before launch, since the smoke fixtures in this pass exercised M1, not L1). Cost
driver: each candidate needs a full Lean compile + kernel check (the sandboxed `lean_worker.py`
path), which is CPU-bound rather than token-bound on the evaluator side; the token cost is the
GEPA/AdaEvolve/sequential proposer calls themselves, each carrying the packet-capped proof context
(no paths, capped size per `test_packet_is_capped_and_has_no_paths`). 10 iterations should be
materially cheaper in tokens than (a) or (b) since there is no per-instance side-information
packet, only the single proof-state packet per call.

No live calls were made to produce these estimates; they are derived from the offline smoke
timing/size evidence cited above, not from a live broker's actual pricing. Get a real quote from
each broker before authorizing a paid run.

## Live checks run (2026-09-25, user-approved, reduced size)

Chain `autoresearch/run-live-checks-260925.sh`, each track gated on its own
approval hash; configs under `*-check*` files. Model gemini-3.8-flash;
reflection model for track 1 corrected to `gemini-3.1-pro-preview` after an
authenticated model listing showed `gemini-3.8-pro` does not exist.

| Track | Arm | Calls | USD | Result |
|---|---|---:|---:|---|
| bound-m (b) | sequential, 20 iterations | 20 | 0.46 | COMPLETE, MORE_CERTIFIED: 7 accepted steps; best certifies 164/303 development families (m=9 74/153, m=10 90/150), worst gap W=4, vs the sweep+LP seed 151/303. Screen 11/30. |
| lean-loop (c) | sequential, 10 iterations | 10 | 0.08 | COMPLETE, MILESTONE_PROGRESS: 3 accepted steps; best 0.06 with helper milestones M1, M4, M6 closed, no target theorem closed. Pipeline (sandboxed Lean build, axiom/sorry checks, packet) works end to end. |
| sort-m9-v3 (a) | gepa seed 1, 20 iterations | see below | | Attempt 1 crashed writing the manifest (relative ledger path; fixed). Attempt 2 stopped at iteration 8: reflection diagnosis truncated at 3000 tokens, GEPA's own retries exhausted the reflection sub-cap (429). Fixed: diagnosis retry-once-then-fallback, reflection max_tokens 8192, ceiling 16. Attempt 3 result appended below. |

Attempts 1 and 2 of track (a) cost $0.40 and $0.40 and reached 1.144 and
1.069 on the 30-instance valset from a seed of 1.004 before stopping.

Track (a) attempt 3 (after the fixes): 17 of 20 iterations, then the
reflection ledger's 16-call ceiling stopped the run (genuine budget
exhaustion, correctly labelled BROKER_STOPPED); 3 valset improvements
(1.004 to 1.069 on the 30-instance metric), 16 flash + 16 reflection calls,
$0.90. Both brokers, the per-instance Pareto path, cascade, rich packets and
the reflection route ran end to end. For the full campaign the reflection
ceiling must be at least 2x iterations. Total live spend for all checks: $2.24.
