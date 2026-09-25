# Lift campaign finalists (lift-m9-260924)

Evaluator `lift-eval-2`. Development sha256 `949f7489769ad6f0`, holdout sha256 `d50a7aef53c3fb5f`. Holdout was evaluated once, after the finalists were frozen. Certificates are finite: exact bounds for listed m=9 unit-base families (all block lengths via Lemma 1). They are not a proof of the conjecture or of a lifting lemma.

## Arms

| Arm | Model attempts | Valid proposals / evaluated | Invalid / truncated | Accepted | Dev certificates | Holdout certificates | Audit agree (dev / holdout) | USD (ledger) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adaevolve | 60 | 17 / 44 | 27 / 18 | 4 | 337/4588 | 190/2295 | 337/337 / 190/190 | 1.0262 |
| evox | 67 | 8 / 8 | 25 / 26 | 4 | 337/4588 | 190/2295 | 337/337 / 190/190 | 0.8556 |
| gepa | 78 | 49 / 51 | 28 / 25 | 14 | 336/4588 | 190/2295 | 336/336 / 190/190 | 1.7330 |
| sequential | 60 | 16 / 16 | 44 / 8 | 5 | 334/4588 | 190/2295 | 334/334 / 190/190 | 0.7704 |
| naive-control | 0 | - / - | - / 0 | - | 285/4588 | 158/2295 | 285/285 / 158/158 | 0.0000 |

Development re-run versus arm claims: all agree.

Accepted means: GEPA candidates added to its pool; sequential greedy screen improvements; AdaEvolve/EvoX new best screen scores (every valid SkyDiscover child enters the database). Truncated counts provider responses with finish_reason length.

## Mechanism evidence

- **adaevolve** (`live-adaevolve-260924-202218`): `{"configured_iterations": 50, "observed_iterations": 50, "successful_generation_iterations": 50, "ucb_island_visits": [23, 22], "ucb_min_visits": 3, "ucb_min_visits_reached": true, "migration_interval": 15, "migration_opportunity": true, "paradigm_window": 10, "paradigms_tried": 10}`
- **evox** (`live-evox-260924-204716`): `{"configured_solution_iterations": 40, "generated_strategy_artifacts": ["/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/lift-m9-260924/live-evox-260924-204716/output/sky/search/iteration_1/code.py", "/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/lift-m9-260924/live-evox-260924-204716/output/sky/search/iteration_2/code.py", "/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/lift-m9-260924/live-evox-260924-204716/output/sky/search/iteration_3/code.py", "/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/lift-m9-260924/live-evox-260924-204716/output/sky/search/iteration_4/code.py", "/Users/pavluhin/Documents/Projects/lrx-lab/autoresearch/lift-m9-260924/live-evox-26`
- **gepa** (`live-gepa-260924-193513`): `{"reflection_batches": 77, "mandatory_hard_case_ids": [], "model_valid_responses": 51, "model_preflight_failures": 26, "best_idx": 11, "lineage_parents": [[null], [0], [1], [2], [1], [4], [5], [3], [6], [4], [4], [10], [10], [7], [8]]}`
- **sequential** (`live-sequential-260924-200000`): `{"accepted_steps": [1, 37, 49, 55, 57], "packet_seen_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]}`

## Families

- **development**: naive certifies 285 child families. The union of engine finalists certifies 337, and 52 of those are not certified by naive. Per arm: {'adaevolve': 337, 'evox': 337, 'gepa': 336, 'sequential': 334, 'naive-control': 285}.
- **holdout**: naive certifies 158 child families. The union of engine finalists certifies 190, and 32 of those are not certified by naive. Per arm: {'adaevolve': 190, 'evox': 190, 'gepa': 190, 'sequential': 190, 'naive-control': 158}.

Families certified by a finalist but not by naive (holdout first; at most 40 per set):

- holdout: `m9-mask1001-labels148967532` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1002-labels927364158` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1006-labels974261538` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1018-labels973512648` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1021-labels735126489` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1022-labels926417538` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask1022-labels942137568` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask135-labels127964853` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask397-labels975164238` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask399-labels975164238` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask431-labels267891543` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask485-labels183647529` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask501-labels273641589` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask503-labels742615389` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask509-labels735126489` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask511-labels264175389` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask511-labels421375689` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask534-labels745931286` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask534-labels749531286` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask875-labels859241763` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask875-labels895241763` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask879-labels895241763` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask932-labels589637241` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask940-labels589637241` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask965-labels183964752` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask965-labels189364752` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask970-labels918364752` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask971-labels918364752` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask973-labels189364752` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask980-labels389672541` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask988-labels389672541` by adaevolve, evox, gepa, sequential
- holdout: `m9-mask992-labels961432578` by adaevolve, evox, gepa, sequential
- development: `m9-mask1003-labels895374261` by adaevolve, evox, gepa, sequential
- development: `m9-mask1007-labels895374261` by adaevolve, evox, gepa, sequential
- development: `m9-mask1014-labels926154738` by adaevolve, evox, gepa, sequential
- development: `m9-mask1022-labels963745128` by adaevolve, evox, gepa, sequential
- development: `m9-mask1022-labels973165248` by adaevolve, evox, gepa, sequential
- development: `m9-mask170-labels892756431` by adaevolve, evox, gepa, sequential
- development: `m9-mask174-labels892756431` by adaevolve, evox, gepa, sequential
- development: `m9-mask201-labels972361548` by adaevolve, evox, gepa, sequential
- development: `m9-mask203-labels972361548` by adaevolve, evox, gepa, sequential
- development: `m9-mask299-labels675413289` by adaevolve, evox, gepa, sequential
- development: `m9-mask303-labels721654389` by adaevolve, evox, gepa, sequential
- development: `m9-mask340-labels684712359` by adaevolve, evox
- development: `m9-mask349-labels514376289` by adaevolve, evox, gepa, sequential
- development: `m9-mask359-labels712564389` by adaevolve, evox, gepa, sequential
- development: `m9-mask367-labels146897532` by adaevolve, evox, gepa, sequential
- development: `m9-mask377-labels632547189` by adaevolve, evox, gepa, sequential
- development: `m9-mask431-labels716894352` by adaevolve, evox, gepa, sequential
- development: `m9-mask471-labels425176389` by adaevolve, evox, gepa, sequential
- development: `m9-mask479-labels714536289` by adaevolve, evox, gepa, sequential
- development: `m9-mask507-labels261547389` by adaevolve, evox, gepa, sequential
- development: `m9-mask509-labels395716428` by adaevolve, evox, gepa, sequential
- development: `m9-mask509-labels935716428` by adaevolve, evox, gepa, sequential
- development: `m9-mask511-labels637451289` by adaevolve, evox, gepa, sequential
- development: `m9-mask511-labels731652489` by adaevolve, evox, gepa, sequential
- development: `m9-mask511-labels935716428` by adaevolve, evox, gepa, sequential
- development: `m9-mask54-labels614952783` by adaevolve, evox, gepa, sequential
- development: `m9-mask598-labels967541328` by adaevolve, evox, gepa, sequential
- development: `m9-mask606-labels972165438` by adaevolve, evox, gepa, sequential
- development: `m9-mask609-labels185697324` by adaevolve, evox, gepa, sequential
- development: `m9-mask610-labels918567324` by adaevolve, evox, gepa, sequential
- development: `m9-mask623-labels136897452` by adaevolve, evox, gepa, sequential
- development: `m9-mask680-labels968471235` by adaevolve, evox, gepa
- development: `m9-mask698-labels951437628` by adaevolve, evox, gepa, sequential
- development: `m9-mask718-labels971256438` by adaevolve, evox, gepa, sequential
- development: `m9-mask748-labels947126358` by adaevolve, evox, gepa, sequential
- development: `m9-mask754-labels963254718` by adaevolve, evox, gepa, sequential
- development: `m9-mask811-labels675413289` by adaevolve, evox, gepa, sequential
- development: `m9-mask847-labels564897321` by adaevolve, evox, gepa, sequential
- development: `m9-mask850-labels423689175` by adaevolve, evox, gepa, sequential
- development: `m9-mask861-labels514376289` by adaevolve, evox, gepa, sequential

## Independent audit

The audit uses integrations/lift_audit.py, which does not import the evaluator. It loads the independent m=8 checker with M=9 and rebuilds each child from the parent. It replays every returned word, checks the Lemma 1 lift at z=0, e_j, 2e_j and all adjacent pairs, and checks the claimed exact mixture witness.
Disagreements: 0.

## Success levels

- **Operational:** yes. At least one native engine produced valid evolving candidates, with the mechanism traces above.
- **Mathematical:** finite only. The finalists certify 84 audited m=9 unit-base child families (development plus holdout) that the naive control does not. Each is an exact family bound. No uniform label-insertion lemma was found or proved, and the conjecture remains open.
- **Comparative:** not established. Each arm ran one seed with one model and budget. The best holdout count among arms is 190, against naive 158. The sequential control is included, but differences are descriptive and do not rank the engines.

## Limitations

- One seed per arm and a single campaign, so there are no confidence intervals and no engine ranking.
- The packet's best-so-far line was stale within some requests: it reflects the verifier state when the packet was built, not later improvements.
- 4096-token output truncations are concentrated on long programs. Truncated proposals count as attempted failures and were never repaired.
- AdaEvolve seed copies and migrants carry no evaluator artifacts upstream, so some of its proposals had no packet.
- Ledger attribution uses run time windows. Spend outside the finalist runs is listed separately.
- Finite development and holdout families only. A miss or timeout proves nothing.
