# bound-m campaign 2 (bound-m-c2-260925)

Date 2026-09-25. Offline build only. No provider call has been made and none is authorized.
`payload-approved.sha256` does not exist; only a human writes it after review.

The contract, evaluator, Lemma 1 pricing and criterion (7) are unchanged from campaign 1
(`autoresearch/bound-m-260925/TASK.md`, evaluator `bound-eval-2`). The main conjecture stays
open. A certificate proves a bound only for its own family. A miss, crash or timeout proves nothing.

## What changed from campaign 1

| item | campaign 1 | campaign 2 |
|---|---|---|
| seed | (b16) sweep-16 | c1 EvoX finalist, docstring rewritten (`seed/evox-c1-seed.py`) |
| model selection | best development score | best **validation** score among each run's accepted candidates |
| holdout | m = 9, 10, 11 | 165 fresh m = 12 plus 60 fresh m = 11 |
| seeds | 1 run per arm | 3 seeds per arm (SkyDiscover `random_seed`, GEPA `EngineConfig.seed`) |
| ledgers | per arm | per (arm, seed), `broker-ledger-bound-c2.<arm>-s<seed>.json` |
| packet | `BOUND_PACKET_V1` | `BOUND_PACKET_V2`: order class; for reversal-orbit failures, the binding constraint and the best word's crossing profile |
| word pool | none | per-run development word pool; packet reports pool alone vs pool + candidate (pool_gain) |
| hint | none | 3 packet lines from the group's m=8 reversal trees (REVERSAL-OBSTACLE.md section 2) |
| report | one number per arm | per arm n, mean, SD, min, max on validation and holdout; generalization gap |

## Sets (`frozen/manifest.json`, built by `build_frozen_c2.py`)

- **development**: campaign 1 `frozen/development.json` by reference and sha256 (303 families,
  m = 9 and 10, the same 30-family screen). Engines, packets and prompts see only this set.
- **validation**: the 165 m = 11 families of the campaign 1 holdout, copied verbatim.
  Finalize uses them only to choose each (arm, seed) finalist.
- **holdout**: 165 m = 12 families (k = 2..12, 15 per k, classes 4/3/2/3/2/1 as the c1 m = 11
  holdout) and 60 m = 11 families (the same class totals x4 over k = 2..12). Seed 260925. They are
  disjoint from every campaign 1 family. k = 13 at m = 12 has a single mask and is not drawn.
  Evaluated once per frozen finalist, by finalize.

## Word pool and hint

Each run keeps a development-only word pool in `<run>/verified/pool.json`. Valid words enter from
the seed and from every candidate that gets a full development evaluation. A GEPA candidate
enters once it has been evaluated on all 30 screen families. Dominated cost vectors are pruned.
Each evaluation reports three counts over the families it covered: the pool alone, the pool plus
the candidate's words, and the candidate alone. pool_gain is the second count minus the first.
The packet names up to 3 newly certifiable families with the pool words they needed.
Selection and every claim use standalone counts only. Validation and holdout ids are refused by
the pool.

The hint quotes m=8 facts only: 4054 of 4088 reversal-orbit families closed with one mixture,
34 needed trees, and the analogue of (m..1){0,m} closed with two mirrored words.

## Budget

`max_usd` is 60, raised from 30 by the orchestrator. That gives a pool of min(floor(60 / 0.1666368), 400) = 360
contacts. Each run has a sub-cap of 30 and makes 30 iterations, so 12 x 30 = 360 fits the pool. EvoX spends
about 2 contacts on startup probes. Campaign 1 charged about $0.02 per call, so the expected spend is about $8.

## Commands

    python autoresearch/bound-m-c2-260925/build_frozen_c2.py        # done; refuses to overwrite
    bash autoresearch/bound-m-c2-260925/run-smokes-c2.sh             # offline mock smokes and captures
    python -m integrations.bound_c2_finalize controls                 # controls on dev + validation
    python -m integrations.bound_c2 approval-hash --write-material autoresearch/bound-m-c2-260925/approval-material.json
    bash autoresearch/bound-m-c2-260925/run-campaign-c2.sh           # live; needs payload-approved.sha256

The runner interleaves seeds (s1 for all four arms, then s2, then s3). It stops on a `HALT` file,
on a refused start, on FIRST_PROMPT_MISMATCH, or after 2 runs that end INCOMPLETE or BROKER_STOPPED.
It then runs `integrations.bound_c2_finalize finalize`.

## Claim rule

An arm claims progress only if its mean holdout certified percentage over the three seeds beats
both control (b) and the seed. A win by a single seed is reported but not claimed.
