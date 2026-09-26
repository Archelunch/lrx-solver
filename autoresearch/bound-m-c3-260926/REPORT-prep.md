# Bound campaign 3: offline preparation report (2026-09-26)

Prepared offline by an Opus worker; written up by the team lead from its
report. No provider call, no commit, no `payload-approved.sha256`. The m=12
holdout file was never opened. All captures used loopback mocks only.

## What was built

- `integrations/bound_c3.py`: driver on the bound-eval-3 tree contract
  (tree SYSTEM and OBJECTIVE, packet BOUND_PACKET_V3, kill-check, approval
  hash); reuses `bound_c2`. Tests `tests/test_search_bound_c3.py` (8, offline).
- `seed/c3-seed.py` (sha256 `6c780864eaedf453...`): AdaEvolve-s2 unchanged,
  then, if its single leaf fails a float LP, an m-uniform refined-origin
  tree: split one axis at a time (most loaded zero first), leaf at lower
  corner l uses origin min(l, 3) on that axis, words from the seed's own
  lift-and-sweep generator on the refined base (no zero-zero swap, no
  table, no m literal), first unbounded passing leaf closes the tree,
  2.3 s CPU stop with single-leaf fallback. The evaluator's exact LP
  decides every leaf.
- `TASK-c3.md` (pre-registered), `campaign-config-c3.json`,
  `broker-config-c3.json`, `mock_api.py`, `run-captures-c3.sh`,
  `run-one-c3.sh`, `run-campaign-c3.sh`, `.gitignore`, `seed_eval_c3.py`,
  `seed-eval/`, `first-prompts/`, `first-prompt-capture/` (ignored).

## Seed results (bound-eval-3, Seatbelt sandbox), vs AdaEvolve-s2 as one leaf

| class | dev seed | dev A-s2 | val seed | val A-s2 |
|---|---|---|---|---|
| rev_rot | 79/85 | 69/85 | 41/44 | 38/44 |
| near_rev | 55/57 | 51/57 | 31/33 | 29/33 |
| refl | 34/38 | 28/38 | 19/22 | 18/22 |
| high_inv | 52/52 | 50/52 | 33/33 | 33/33 |
| uniform | 44/44 | 43/44 | 22/22 | 22/22 |
| easy | 19/19 | 19/19 | 11/11 | 11/11 |
| tight | 0/8 | 0/8 | none | none |
| total | 283/303 | 260/303 | 157/165 | 151/165 |
| worst gap | 15/7 | 15/7 | 4 | 4 |

Closes 23 of the 43 development families AdaEvolve-s2 misses (the
table-fed tree control closes 19), loses none. No invalid, incomplete or
timed-out family. Audit agrees on all 283 and 157. Two fresh sandboxed runs
per set gave identical raw trees. Max CPU 1.90 s (dev), 2.13 s (val).
Validation was measured once, not tuned on (origin cap 4 would add one
development family; kept 3). Still open: m=9 reversal {0,4} at gap 15/7
(the table control closes it with three leaves) and all 8 tight families.

## Decisions taken by the team lead

- USD cap raised from $10 to $15 (projection $11-14 for 360 calls at
  $0.03-0.04 per call with the 21.8 KB seed; c2 was $0.021 with 9.4 KB).
  `approval-material.json` regenerated; current approval hash
  `ebac59b347867592b9b2c48a88f6d1c7498197655eb3878d78cd4b54bd6a7ff0`
  (the worker's earlier `c3de250d...` was for the $10 config).
- Output limit 16384 tokens (c2: 32 of 342 calls hit 8192); contact pool
  360 explicit, USD cap is the hard limit.
- One model for all calls, gemini-3.8-flash (as in c2); re-verify id and
  prices against a live listing before launch.
- Success rule uses the MEAN over an arm's three seed finalists for both
  conditions (holdout share >= seed + 3 points; >= 5 of the 14 c2-missed
  m=12 families, recomputed at finalize from stored c2 rows, abort unless
  exactly 14). Fresh m=11 holdout reported, not scored.
- Kill rule: first 15 fully evaluated distinct proposals of each arm's
  seed-1 run, `python -m integrations.bound_c3 kill-check --seed 1`, exit 3
  stops the campaign; `run-campaign-c3.sh` runs it after the seed-1 runs.
- No word pool in c3 (tree leaves on refined bases do not pool).
- Finalize (`bound_c3_finalize.py`) is being built separately; it must
  compare raw tree outputs for determinism, as `seed_eval_c3.py` does.

## First prompts

12 captures, all exit 0, through `mock_api.py` on 127.0.0.1. Leak checks:
V3 packet present, no m=11/m=12 ids, no validation ids, tree-contract
system prompt in every prompt; the team lead's own grep over the rendered
prompts found only the generic "unseen m" sentence. Identical prompts:
AdaEvolve s1 = s3 (s2 adds SkyDiscover's seed-dependent exploration
block), EvoX and sequential identical across seeds, GEPA differs per seed.

| arm/seed | messages sha256 |
|---|---|
| gepa s1 | 26936e50809a34d4e4c09a2eefe9c3c0cd3d8f02f9c3d52f326288abba972b02 |
| gepa s2 | ffedaeb363386bef4a98b05dfdb19d3122ad044e4dae3636133202c80a0db762 |
| gepa s3 | 8f12e17cd8f342187a7bd7f1ed0e89545fbca9e8ef5fa9c8c4e038641351404b |
| sequential s1-3 | fb2447ebd29cef8c4a258c3686b64875409052fc6a2160e087f4e7caae7cab21 |
| adaevolve s1, s3 | f6e0102e244899047d69d956e5be1f72833555c0066169d32fa094cdbce32ce4 |
| adaevolve s2 | 776e8b368e750a69cf7668c83b35c8d8e1454301255e1a54cd995d2517f569bc |
| evox s1-3 | 9b00325265dd8e9161f5bb641da1e389d37f4e192a145b3da313b77eb7bcef9f |

## Launch (only after human approval written to payload-approved.sha256)

    python -m integrations.bound_c3 approval-hash --campaign-dir autoresearch/bound-m-c3-260926
    set -a; . ./.env; set +a
    bash autoresearch/bound-m-c3-260926/run-campaign-c3.sh
    python -m integrations.bound_c3 campaign-spend --campaign-dir autoresearch/bound-m-c3-260926

Per run: `bash autoresearch/bound-m-c3-260926/run-one-c3.sh <arm> <seed>`
(check-approval, then `live`; broker on port 8895, per-run ledger
`broker-ledger-bound-c3.<arm>-s<seed>.json`, run dir `live-<arm>-s<seed>-<stamp>/`).

## Offline checks

    python -m unittest discover -s tests -p 'test_*.py'   # Ran 612 tests, OK (skipped=4)
    python -m compileall -q src tests integrations        # exit 0
    python -m src.lrx.cli smoke                           # passed: true

## Addendum (2026-09-26, after Session 19)

Hand generators word_A, word_B, word_E (`../bound-m-260925/REVERSAL-WORDS.md`)
certify the family (m..1){0,m} at m = 9..12 and fail from m = 13. At finalize
they are an extra post-hoc control on the {0,m} families only, not part of
the pre-registered success rule; the campaign payload and hash are unchanged.
