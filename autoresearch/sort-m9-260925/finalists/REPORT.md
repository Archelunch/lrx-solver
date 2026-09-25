# sort-m9 campaign finalists (sort-m9-260925)

Evaluator `sort-eval-2`. Development sha256 `f4dd4752758b573c`, holdout sha256 `c281643a330814d4`. The holdout was evaluated once, after the finalists were frozen. A valid word is an upper bound on d(v) for that one state. Within budget means length <= T_m(n). The main conjecture remains open regardless of these results.

## Arms

| Arm | Calls | Valid / evaluated proposals | Invalid / truncated | Accepted | Dev within | Dev mean excess | Dev worst-r rate | Holdout within | Holdout worst-r rate | Holdout m9r1 | Holdout m9r2 | Holdout m9r3 | Holdout m9r4 | Holdout m9r5 | Holdout m9r6 | Holdout m10r3 | Audit disagreements (dev / holdout) | USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adaevolve | 55 | 23 / 43 | 20 / 6 | 8 | 1480/1500 | 0.66 | 0.963 | 2059/2100 | 0.940 | 300/300 | 300/300 | 296/300 | 297/300 | 294/300 | 282/300 | 290/300 | 0 / 0 | 1.0800 |
| evox | 43 | 26 / 30 | 13 / 11 | 6 | 1470/1500 | 0.76 | 0.950 | 2053/2100 | 0.943 | 300/300 | 299/300 | 290/300 | 299/300 | 294/300 | 283/300 | 288/300 | 0 / 0 | 0.8252 |
| gepa | 60 | 50 / 60 | 10 / 0 | 15 | 1494/1500 | 0.44 | 0.983 | 2080/2100 | 0.967 | 300/300 | 300/300 | 297/300 | 300/300 | 298/300 | 290/300 | 295/300 | 0 / 0 | 1.4641 |
| sequential | 60 | 6 / 59 | 53 / 0 | 6 | 1484/1500 | 0.46 | 0.967 | 1918/2100 | 0.453 | 300/300 | 300/300 | 294/300 | 300/300 | 294/300 | 136/300 | 294/300 | 0 / 0 | 1.2064 |
| naive-control | 0 | - / - | - / 0 | - | 128/1500 | 51.80 | 0.067 | 157/2100 | 0.050 | 34/300 | 25/300 | 27/300 | 17/300 | 15/300 | 15/300 | 24/300 | 0 / 0 | 0.0000 |
| sweep-control | 0 | - / - | - / 0 | - | 1356/1500 | 1.83 | 0.830 | 1846/2100 | 0.783 | 300/300 | 291/300 | 262/300 | 268/300 | 255/300 | 235/300 | 235/300 | 0 / 0 | 0.0000 |

Development re-run versus arm claims: all agree.

Calls and USD come from the per-arm broker ledgers. Truncated counts responses with finish_reason length. Accepted means: GEPA candidates added to its pool, sequential greedy improvements, AdaEvolve/EvoX new best combined_score in request order.

## Mechanism evidence

- **adaevolve** (`live-v2-adaevolve-260925-135343`, research_status FIRST_PROMPT_MISMATCH): `{"configured_iterations": 50, "observed_iterations": 50, "successful_generation_iterations": 46, "ucb_island_visits": [27, 22], "ucb_min_visits": 3, "ucb_min_visits_reached": true, "migration_interval": 15, "migration_opportunity": true, "paradigm_window": 10, "paradigms_tried": 10}`
- **evox** (`live-v2-evox-260925-141558`, research_status MORE_WITHIN_BUDGET): `{"configured_solution_iterations": 40, "generated_strategy_artifacts": [], "fallback_strategy_records": [], "strategy_adoption_log_observed": false, "strategy_adopted_confirmed": false, "solution_diff_parse_failures": 9, "evox_meta_search_calls": 0, "evox_solution_calls": 43, "evox_meta_search_share": 0.0}`
- **gepa** (`live-v2-gepa-260925-125146`, research_status MORE_WITHIN_BUDGET): `{"reflection_batches": 0, "mandatory_hard_case_ids": [], "model_valid_responses": 60, "model_preflight_failures": 0, "best_idx": 15, "lineage_parents": [[null], [0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14]]}`
- **sequential** (`live-v2-sequential-260925-131859`, research_status MORE_WITHIN_BUDGET): `{"accepted_steps": [1, 2, 3, 4, 5, 10], "packet_seen_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60], "truncated_steps": []}`
- **adaevolve** admitted despite FIRST_PROMPT_MISMATCH: only SkyDiscover's parent-selection mode-guidance block differs; system message, program and packet byte-identical (checked by sort_finalize.mode_only_difference). Live `799905f23c2b8e85` vs approved `fb0b7a84c6fb7c1b`; its finalist is the best record in verified/evaluations (`candidate-0038.py`), re-executed here. Diff and hashes are in finalists/manifest.json.

## Independent audit

integrations/sort_audit.py does not import sort_evaluator or sort_backends. It re-executes every returned word with its own L/R/X list executor and checks the final vector against (1..m, 0^r). For sorted words it re-checks length <= T and excess = length - d(v), with d(v) from a fresh, sha256-verified DistanceTable load that must match the frozen manifest's table hash.
Words checked: holdout adaevolve 2100; holdout evox 2094; holdout gepa 2100; holdout sequential 1935; holdout naive-control 2100; holdout sweep-control 2100; development adaevolve 1500; development evox 1500; development gepa 1500; development sequential 1500; development naive-control 1500; development sweep-control 1500.
Disagreements: 0.

## Success levels

- **Operational:** yes. At least one native engine produced valid evolving sorting programs, with the mechanism traces above.
- **Mathematical:** finite only. Every audited within-budget word certifies d(v) <= T for its one sampled state. Some finalist sorted every sampled holdout state within T for ['m9r1', 'm9r2', 'm9r4']; that is a statement about the sampled states only, not about every state of that (m, r). No sorting program is proved to meet T on all states, and the main conjecture remains open.
- **Comparative:** not established. One seed, one model and one budget per arm. The best engine finalist (gepa) has 2080 holdout states within budget, against 1846 for the cyclic-sweep control and 157 for the naive seed, out of 2100. These differences are descriptive and do not rank the engines.

## Limitations

- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.
- Development and holdout are finite stratified samples (300 per table, top layers oversampled). All radius states of m=9 r=1..5 are in development, so the m=9 r=1..5 holdout has no state at T.
- A crash, timeout or long word proves nothing about d(v). Truncated proposals were never repaired.
- The packet's best-so-far line reflects the verifier state when the packet was built.
- Version 2 contract: 0.2 s CPU per state, so every finalist is a constructive program. The stopped attempt 1 (live-gepa-260925-120053, per-state search under the 2 s v1 limit) is excluded.
- The (9,6) holdout uses T_9(15) = 80 while its exact radius is 79; (10,3) uses T_10(13) = 71.
