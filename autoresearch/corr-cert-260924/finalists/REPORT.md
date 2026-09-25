# corr-cert campaign finalists (corr-cert-260924)

Evaluator `corr-eval-1`. Development sha256 `95fab8d7159cfc8f`, holdout sha256 `37872712a0eca08e`. Holdout was evaluated once, after the finalists were frozen. A pass is an exact THEOREM.md certificate for that m (corrcert.check_certificate, epsilon < 1). Development is m=4..12, holdout is m=13..20; passing every development m is not a proof for general m, and the main conjecture remains open regardless of these results.

## Arms

| Arm | Model attempts | Valid proposals / evaluated | Invalid / truncated | Accepted | Dev passes | Holdout passes | Min violation_sum on a miss (dev) | Audit agree (dev / holdout) | USD (ledger) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adaevolve | 84 | 21 / 40 | 19 / 39 | 5 | 2/9 | 0/8 | 1293.667 | 2/2 / 0/0 | 2.3356 |
| evox | 23 | 0 / 0 | 0 / 11 | 0 | 0/9 | 0/8 | 264.000 | 0/0 / 0/0 | 0.5131 |
| gepa | 66 | 30 / 30 | 1 / 15 | 5 | 2/9 | 0/8 | 184.667 | 2/2 / 0/0 | 1.6671 |
| sequential | 63 | 1 / 1 | 59 / 15 | 1 | 2/9 | 0/8 | 1170.000 | 2/2 / 0/0 | 1.2042 |
| naive-control | 0 | - / - | - / 0 | - | 0/9 | 0/8 | 264.000 | 0/0 / 0/0 | 0.0000 |

Development re-run versus arm claims: all agree.

Ledger attempts outside the finalist runs: unattributed: 17 attempts, $0.3635

Accepted means: GEPA candidates added to its pool; sequential greedy screen improvements; AdaEvolve/EvoX new best combined_score (every valid SkyDiscover child enters the database; unlike lift there is no per-parent screen/full split here, so this is a strict full-development improvement, not a screen promotion). Truncated counts provider responses with finish_reason length.

## Mechanism evidence

- **adaevolve** (`live-adaevolve-260924-234707`): `{"configured_iterations": 50, "observed_iterations": 50, "successful_generation_iterations": 48, "ucb_island_visits": [24, 23], "ucb_min_visits": 3, "ucb_min_visits_reached": true, "migration_interval": 15, "migration_opportunity": true, "paradigm_window": 10, "paradigms_tried": 10}`
- **evox** (`live-evox-260925-000506`): `{"configured_solution_iterations": 40, "generated_strategy_artifacts": [], "fallback_strategy_records": [], "strategy_adoption_log_observed": false, "strategy_adopted_confirmed": false, "solution_diff_parse_failures": 0}`
- **gepa** (`live-gepa-260924-232519`): `{"reflection_batches": 31, "mandatory_hard_case_ids": [], "model_valid_responses": 30, "model_preflight_failures": 1, "best_idx": 5, "lineage_parents": [[null], [0], [1], [2], [3], [4]]}`
- **sequential** (`live-sequential-260924-233143`): `{"accepted_steps": [27], "packet_seen_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]}`

## Independent audit

The audit uses integrations/corr_audit.py, which does not import corr_evaluator or corr_task. It loads a fresh copy of autoresearch/corr-cert-260924/corrcert.py, reimplements the JSON-safe coefficient-key decoding from scratch, and re-checks (5), (6) and epsilon<1 exactly for every m an arm claims a pass on.
Disagreements: 0.

## Success levels

- **Operational:** yes. At least one native engine produced valid evolving candidates, with the mechanism traces above.
- **Mathematical:** finite only. The finalists certify m in [4, 5] (development) and [] (holdout) that the naive control does not; each is an exact, audited THEOREM.md certificate for that single m. No universal formula was found or proved for coefficients(m), and the main conjecture (and Theorem 1 beyond m=16) remains open.
- **Comparative:** not established. Each arm ran one seed with one model and budget. Best development passes among arms is 2 against naive 0; best holdout passes is 0 against naive 0. The sequential control is included, but differences are descriptive and do not rank the engines.

## Limitations

- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.
- The packet's best-so-far line was stale within some requests: it reflects the verifier state when the packet was built, not later improvements.
- Truncated proposals (finish_reason length) count as attempted failures and were never repaired.
- AdaEvolve seed copies and migrants carry no evaluator artifacts upstream, so some of its proposals had no packet.
- Ledger attribution uses run time windows. Spend outside the finalist runs is listed separately.
- Finite development and holdout m-sets only (4..12, 13..20). A miss or timeout proves nothing about any m, and this evaluates coefficients(m) as given, not any symbolic argument for why it should hold generally.
