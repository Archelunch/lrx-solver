# Iteration report: independent replication of the external m=8 package

Date 2026-09-24. Orchestrator: Claude Fable 5.1. Workers: one Opus agent
(independent checker), one Sonnet agent (k5 compatibility test).
No provider call, no new dependency, no commit, no push.

## Goals agreed with the user

1. Layer A: run the package's own replay unchanged.
2. Layer B: independent stdlib checker from the theorem text.
3. k5-mask302-order15713 as a compatibility test only.
4. Claims stay attributed; repo flips only after audit.
5. Optimizer moves to m=9 after the audit. Cap $8 / 20 contacts approved,
   nothing spent.

## Inputs

`downloads/recent/lrx_m8_complete_verification` copied to `package/`
(gitignored). Manifest: 147 SHA-256 entries, 0 mismatch, 0 missing.

## Layer A: package replay

`replay-full.json`: status PASS, 30 stages, 1009.6 s wall, nice 10.
Longest stage `low_resources` 425 s. Completion audit: 20,603,520 families,
0 remaining, 5 negative controls rejected. Logs in `package/m8_replay_logs/`.

## Layer B: independent checker

`checker/` (lrxm8.py, check_stage.py, union.py), stdlib and Fractions only,
no package script imported. Full results in `checker-report.md`.

| Stage | Families | Failed | Stored-claim mismatches |
|---|---:|---:|---:|
| four (+14 trees) | 262,513 | 0 | 0 |
| five (+4 trees) | 337,965 | 0 | 0 |
| six (+2 trees) | 228,966 | 0 | 0 |
| seven | 74,614 | 0 | n/a |
| eight | 10,278 | 0 | n/a |
| nine | 40,320 | 0 | n/a |
| reverse trees | 4,088 | 0 | 0 |

Union rebuilt over all 8! x 382 masks with k>=4, no package coverage table:
0 uncovered, per-k counts equal the package table. Low blocks: 338 one-block
exception mixtures, 37,323 two-block trees, 639,357 three-block trees all
pass. Five corrupted records rejected. Wall: 2081 s union, about 15 min for
the stage files, 6 processes.

## k5 compatibility test

`k5-mask302/REPORT.md`: family certified by Lemma 4 projection from seven-gap
record 37688 (mask 446). Weighted base 121/2 < 61, slopes (6, 63/11, 6, 6, 6).
Stdlib replay and repo evaluator agree. Our pool optimum was 1223/20.

## Exact mathematical progress and optimizer contribution

- New theorem proved here: none. The m=8 bound is the group's result.
- New independent evidence: two replications of the package, one of them
  written independently from the theorem text.
- Optimizer contribution this iteration: zero. No proposer ran.

## Not replicated

Low-block single-word certificates were replicated by an independent stdlib
bounded search written from the section 7 resource table (`checker/lowsearch.py`):

| k | Bases searched | Words found | Exception agreement |
|---|---:|---:|---|
| 1 | all 362,880 | 362,542 | the 338 no-word bases equal the package's 338 exactly |
| 2 | 5,000 seeded + 420 listed exceptions | 4,891 | all 109 no-word bases are listed; all 420 exceptions have no word |
| 3 | 5,000 seeded + 160 listed exceptions | 4,478 | all 491 three-block no-word bases listed; all 160 exceptions have no word |

Still not replicated: full enumeration of the 1.81M k=2 and 6.65M k=3 bases;
the remaining listed exceptions; the 290 and 65+36,888 fewer-block exception
counts (not listed in the package, only stated); the increment table itself
(supported only by exact resource/slope agreement on 371,911 found words);
Lean modules; C++ programs; n>=130 theorem (not needed). Lemmas 1-4 read and
re-derived, not formalised. "No word in this class" is never infeasibility.

## Repo verification

380 tests OK (1 pre-existing skip), compileall OK, CLI smoke pass, trusted
lock `{"ok": true}`. New test file `tests/test_search_m8checker.py`.

## Next iteration

Freeze an m=9 development set and holdout (exclude nothing consumed at m=8,
since m=9 is new ground, but record hashes before any search). Determine
T_9(n). Fix proposer transport with mock tests. Then the matched sequential
vs GEPA pilot within $8 / 20 contacts.
