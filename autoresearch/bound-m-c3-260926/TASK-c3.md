# bound-m campaign 3 (bound-m-c3-260926): pre-registered spec

Date 2026-09-26. Offline build only. No provider call has been made and none is authorized.
`payload-approved.sha256` does not exist; only a human writes it after review.

The main conjecture stays open. A certificate proves d(v) <= T_m(n) only for its own family,
conditional on the research group's Lemma 1 with refinement and criterion (8). A miss, crash or
timeout proves nothing.

## Objective

Evolve an m-uniform `certify(family)` that emits tree certificates (bound-contract-3, evaluator
bound-eval-3, `integrations/bound3_*.py`) and closes the reversal orbit (rev_rot, near_rev, refl)
at unseen m with no exact tables. Score per candidate is bound-eval-3's combined score: mean over m
of the certified percentage, plus the worst m again, plus small terms for valid output and a small
worst gap (worst leaf gap per family, then max per m). Sandbox, 3 s CPU per family, source guard and
invalid gap 4000 are bound-contract-2's, unchanged.

## Splits

| split | families | use |
|---|---|---|
| development | campaign 1 `frozen/development.json`, 303 families, m = 9, 10 (30-family screen) | engines, packets, prompts |
| validation | campaign 2 `frozen/validation.json`, 165 families, m = 11 | kill check and finalist selection only |
| holdout | campaign 2 `frozen/holdout.json`, 165 m = 12 + 60 m = 11 | one shot per frozen finalist, never in prompts |

All three are the campaign 2 files, fixed by hash in `autoresearch/bound-m-c2-260925/frozen/manifest.json`.
The engine side refuses any family with m outside {9, 10} and never opens the holdout file.
The seed check (`seed_eval_c3.py`) and the capture mock read only development and validation.

## Seed and controls

- **Seed**: `seed/c3-seed.py`. It is the campaign-2 AdaEvolve-s2 finalist, code unchanged, plus a
  table-free refined-origin staircase. Offline results are in `seed-eval/summary.json` and `REPORT-prep.md`.
- **Control (a)**: AdaEvolve-s2 as one unit-origin leaf, `autoresearch/bound-eval3-260926/adaevolve-s2-wrapped.py`.
- **Control (b)**: the table-fed staircase `integrations.bound3_control_revtree`. It is trusted, runs
  in-process and uses exact tables, so it is a non-uniform reference on m <= 10 only
  (`autoresearch/bound-eval3-260926/control-b.jsonl`). It is never run at m = 11 or 12.

## Arms, seeds, models, budget

- Arms: GEPA, sequential control, AdaEvolve, EvoX (strategy evolution off). Each arm runs 3 seeds
  of 30 iterations. SkyDiscover `random_seed` and GEPA `EngineConfig.seed` equal the run seed.
- Model: gemini-3.8-flash for every call, reasoning effort low, max_tokens 16384.
  Campaign 2 used no separate reflection model, so gemini-3.1-pro-preview is not used.
- Budget: $10 total, enforced by each run's broker at max_usd minus the spend in the other c3 ledgers.
  Contact pool 360 is 12 runs x 30. Ledgers are per (arm, seed): `broker-ledger-bound-c3.<arm>-s<seed>.json`.
- Order: s1 of all arms, then the kill check, then s2, then s3 (`run-campaign-c3.sh`).
  The runner stops on a HALT file, a refused start, FIRST_PROMPT_MISMATCH, or 2 runs ending INCOMPLETE or BROKER_STOPPED.
- Packet BOUND_PACKET_V3 covers development only. It gives totals, best so far, and up to 3 failing
  families, each with its tree summary, worst leaf (box, origins, T(l), LP lhs, slope excess) and support words.
  It ends with a 3-line hint drawn from m = 8 and m = 9 development facts.

## Kill rule

After the four seed-1 runs, `python -m integrations.bound_c3 kill-check --seed 1` runs. For each arm,
it takes the accepted candidates among its first 15 distinct proposals, meaning those with a full
development evaluation. It evaluates each on validation in the sandbox. If no arm has a candidate that
certifies more validation families than the seed, the campaign stops. The seed certifies 157 of 165
offline. A stop is exit code 3.

## Finalist selection

Selection is per (arm, seed) and uses validation only. The candidates are the seed, every source with a
full development evaluation, the verified best, and GEPA's candidate pool. The finalist has the most
validation certificates. Ties go to the higher validation combined score, then the smaller source sha256.
Development scores play no part. A finalist must pass a determinism check: two sandboxed runs on the
first 20 screen families must give identical raw tree outputs.

## Success rule (pre-registered)

An arm succeeds iff both conditions hold:

1. The mean over its 3 finalists of the certified share on the 165 m = 12 holdout families is at
   least the c3 seed's m = 12 share plus 3 percentage points.
2. The mean over its finalists of the number certified among the 14 target families is at least 5.

The 14 target families are the m = 12 holdout families that none of AdaEvolve-s2, EvoX-s3, the c2
seed and control (b) certify (`BEST-C2-CONSTRUCTION.md` section 2). Finalize recomputes them from the
stored campaign-2 holdout rows and aborts unless there are exactly 14. Single-seed wins are reported
but not claimed. The 60 fresh m = 11 holdout families are reported, not scored.

## Commands

    bash autoresearch/bound-m-c3-260926/run-captures-c3.sh     # done offline: first-prompts/*.{md,sha256}
    python -m integrations.bound_c3 approval-hash --write-material autoresearch/bound-m-c3-260926/approval-material.json
    # human: review the material and first prompts, then write payload-approved.sha256
    bash autoresearch/bound-m-c3-260926/run-campaign-c3.sh     # live; refuses without payload-approved.sha256
