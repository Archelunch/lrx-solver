# Loop hygiene v3, Track 1: change spec for the sort-m9 search loop

Date 2026-09-25. This file is a spec only. No code, config, or run file was changed.
Inputs read: `integrations/{official_backends,lift_backends,sort_backends,sort_evaluator,sort_worker,sort_finalize,research_budget}.py`,
`autoresearch/sort-m9-260925/{campaign-config.json,broker-config.json,TASK.md,REPORT.md,GUARD-NOTE.md}`,
`autoresearch/REPORT-FOR-AGENTS-260925.md`, `autoresearch/TRACE-AUDIT-260925.md`. I checked the engine behavior
by reading the installed packages in `.venv-official`: GEPA 0.1.4 and SkyDiscover 0.2.0. Paths in §1 are
relative to `site-packages/`.

State checked today: `python tools/orchestrator.py trusted` returns `{"ok": true, "changed": [], ...}`, and
`python -m integrations.sort_backends approval-hash` returns `7626d6b0...a328`, which equals
`sort-m9-260925/payload-approved.sha256` (v2 is still reproducible).

## 0. Decisions that shape the plan

**D1. Add new modules and leave the approved ones unchanged.** The v2 approval hash covers the bytes of
`sort_backends.py`, `lift_backends.py` and `official_backends.py`. The lift and corr campaigns and 491 tests also
depend on `lb` and `ob`. v3 therefore goes into new files:

| New file | Role |
|---|---|
| `integrations/sort_loop3.py` | v3 backends: verifier, packet v2, engine configs, GEPA worker, sequential, launch, live, approval |
| `integrations/sort_loop3_finalize.py` | per-(arm, seed) finalists, one holdout pass, mean and spread per arm |
| `autoresearch/loop-v3-260925/build_instances.py` | frozen instance partition and screen subset |
| `autoresearch/loop-v3-260925/{campaign-config.json, broker-config.json, broker-config-reflection.json, run-one.sh, run-campaign.sh, mock_api.py}` | campaign inputs |
| `tests/test_search_sort_loop3.py`, `tests/test_search_sort_loop3_finalize.py` | offline tests, with mock HTTP only |

The following stay unchanged: `sort_evaluator.py` and `sort_worker.py` (so `evaluator_hash()`, and with it the scores,
stay comparable to v2), `sort_backends.py`, `lift_backends.py`, `official_backends.py`, `research_budget.py`,
`sort_finalize.py`, and every TRUSTED file. None of the new files are in `tools/orchestrator.py` TRUSTED, so `trusted`
stays ok. `sort_loop3.py` imports from `sort_backends` (`SYSTEM`, `OBJECTIVE`, `STRUCTURAL_FACTS`,
`preflight_source`, `per_r_line`, `_worst`, `tables_from_manifest`, `first_prompt_mismatch`, `is_solution_request`,
`verify_first_solution_prompt`, `_research_status`, `_RESULT_KEYS`, `SortBrokerLM`) and from `lb`/`ob`. Its top
level imports only the standard library and those three modules, the same sandbox-staging rule as
`sort_backends`. `_launch_v3` also stages `sort_backends.py`.

**D2. Reuse the sort-m9-260925 frozen development set and holdout** (manifest `c98fd613...`). v3 numbers are then
directly comparable with the v2 single-seed table. Caveat: v2 holdout results shaped the v3 design, but they never
selected a candidate. Open decision O1 covers a fresh holdout.

**D3. Seeds `[1, 2, 3]`, the same values for every arm** (matched replicates).

## 1. Engine facts that drive the design (verified in the installed code)

| Fact | Where |
|---|---|
| SkyDiscover `DatabaseConfig.random_seed` defaults to `None` and `base_database` seeds `random.Random(None)`, which draws from OS entropy. AdaEvolve draws the parent-selection mode on every iteration; the EvoX initial strategy samples parents with the same RNG. | `optimize/config.py:401`, `optimize/search/base_database.py:95`, `adaevolve/database.py:559,634`, `evox/database/initial_search_strategy.py:66-80` |
| Proxy order in `compute_proxy_score`: `fitness_key`, then `combined_score`, then the mean of the Pareto objectives, then `get_score`, which is the mean of all numeric metrics (bools excluded). With Pareto on, `_is_better` uses this proxy. v2 always returned `combined_score`, so v2 never reached the averaging fallback. SkyDiscover's own failure results do reach it: `{"error": 0.0}` and `{"error": 0.0, "timeout": True}` give a proxy of 0.0. | `optimize/utils/metrics.py:9-16,78-120`, `base_database.py:291-300`, `evaluation/evaluator.py:262-275` |
| A missing Pareto objective becomes `-inf`, so an incomplete metric vector cannot dominate a complete one. | `optimize/utils/pareto.py:108-128` |
| Cascade: only `cascade_thresholds[0]` is used. If stage 1 fails the threshold, the stage-1 metrics become the program's metrics. If it passes, the result is the numeric merge `{**stage1, **stage2}` with `error` dropped. The threshold reads `combined_score`, or falls back to the mean of numerics. The default is `cascade_evaluation=True`; v2 set it to False. | `evaluation/evaluator.py:247-318`, `config.py:369-370` |
| `inject_evaluator_context=None` means "auto", which turns on only when there is no seed program or for a Harbor task. v2 had a seed, so it was off. However, AdaEvolve's `ParadigmGenerator` always receives `evaluator_code=self._load_evaluator_code()`, so paradigm prompts contain the staged `evaluator.py` source whatever that flag says. | `optimize/runner.py:80-90`, `adaevolve/controller.py:80-112`, `adaevolve/paradigm/generator.py:323,345` |
| AdaEvolve puts `artifacts["feedback"]` into the prompt truncated to 2000 chars. `format_artifacts` renders every other artifact key, each truncated to 2000. EvoX uses `format_artifacts`. | `context_builder/adaevolve/builder.py:281-305`, `context_builder/utils.py:47-65` |
| `llm.guide_models` serve AdaEvolve paradigm calls. A per-model `api_base` that is set explicitly is kept, because `update_model_params` fills only `None` fields. | `config.py:225-245,271-277`, `adaevolve/controller.py:77-92` |
| `lb.evox_strategy_evolution_enabled` returns True when `iterations >= 100`. **At 200 iterations the v2 code path would turn EvoX's LLM-written search strategies on.** | `integrations/lift_backends.py:406-437` |
| GEPA `optimize_anything` sets `reflection_minibatch_size` to 3 unless in single-instance mode. Other defaults: `frontier_type="hybrid"`, `candidate_selection_strategy="pareto"`, `EngineConfig.seed=0`, `parallel=True` with `max_workers=cpu_count`, `cache_evaluation=False`. `batch_evaluator` receives all pending (candidate, example) pairs in one call. `refiner` defaults to None. GEPA has no separate proposer model: `reflection_lm` itself writes the candidate. | `gepa/optimize_anything.py:452-497,717-750,1114-1290`; `adapters/optimize_anything_adapter/optimize_anything_adapter.py:57-160` |
| The research broker refuses any request whose `model` differs from its own. A second model therefore needs a second broker with its own ledger. | `integrations/research_budget.py:556-557` |
| v2 full-development evaluation (1500 states) wall time per candidate: median 9-23 s and maximum 45 s across the four v2 runs. | `live-v2-*/verified/evaluations/result-*.json` `seconds` |

## 2. Frozen v3 inputs (new, deterministic, hashed)

`autoresearch/loop-v3-260925/build_instances.py` uses only the standard library. It reads
`sort-m9-260925/frozen/development.json` after checking its hash against that manifest. It writes
`frozen-v3/instances.json`, `frozen-v3/screen-ids.json` and `frozen-v3/manifest.json`. The manifest records the
source manifest sha, dev sha, instances sha, screen sha and the rule text. The script refuses to overwrite existing
files.

- **Instances (30).** For each r in 1..5, sort that r's 300 development states by `(d, id)` and cut them into 6
  consecutive groups of 50, named `r{r}-s{k}`, where k=1 is the lowest d. Every development state lands in exactly one
  instance. The d ranges run from `r1-s1` (d 1..17) to `r5-s6` (d 70..73).
- **Screen (100).** For each r, take every state at the table radius (1, 2, 5, 1, 6 states for r=1..5). Fill up to
  20 per r with evenly spaced picks from the remaining states in `(d, id)` order: index
  `int(step*i + step/2)` with `step = len(rest)/need`. The screen is a subset of the development set.

Measured from saved per-state rows, with no candidate executed (`controls/v2-sort_control_sweep-development.json`,
`finalists/development-results.json`; script in the session scratchpad):

| Program | Screen combined (within/100) | Full combined (within/1500) |
|---|---:|---:|
| naive control | 0.0645 (6) | 0.1234 (128) |
| sweep control (seed) | **1.1887** (80) | 1.4075 (1356) |
| v2 AdaEvolve best | 1.4565 (93) | 1.6186 (1480) |
| v2 EvoX best | 1.4962 (93) | 1.5973 (1470) |
| v2 sequential best | 1.5748 (95) | 1.6434 (1484) |
| v2 GEPA best | 1.6473 (98) | 1.6610 (1494) |

The screen ranks programs almost as the full set does. It is harder than the full set because it holds all 15
radius states.

**Instance saturation.** The seed already has 50/50 within budget on 18 of the 30 instances, and the v2 GEPA best on
28 of 30. Neither is at excess 0 on every state of any instance. The instance score (§3.2) therefore has to carry an
excess term, or instance-level Pareto gets no signal on 18 instances. An alternative partition (lower 120 states as
2x60, top 180 as 4x45) also left 18 saturated, so the simple sextile partition stays.

## 3. Changes, item by item

### 3.1 Explicit seeds (item 1)

In `sort_loop3.py`:

- `campaign-config.json` gets `"seeds": [1, 2, 3]`.
- `engine_knobs(cc, engine, seed) -> dict` is a pure function. It is the single source of every engine setting,
  used both to render configs and in the approval material (§3.10).
- `_sky_config_v3(args, stage)` builds the SkyDiscover config from scratch, not through `lb._sky_config`. It sets
  `search.database.random_seed = seed` for AdaEvolve and EvoX, and `max_parallel_iterations: 1` explicitly.
- `_gepa_worker_v3` uses `EngineConfig(seed=seed)`, replacing the hard-coded `seed=0` in
  `sort_backends._gepa_worker` line 471. The `epoch_shuffled` minibatch order follows this seed.
- Sequential has no RNG. The seed is recorded in the manifest and the run name only, so the three sequential runs are
  provider-sampling replicates. No provider `seed` field is sent: support is unverified, and it would change the
  dry-run payload.
- CLI `live --engine E --seed S` creates run dir `live-v3-{engine}-s{S}-{stamp}` and ledgers per (engine, seed)
  (§3.11).
- First-prompt guards per (arm, seed) in `first-prompt-{engine}-s{S}.sha256`, 12 files. Each hash is captured twice
  through the mock in independent 1-iteration runs, and both captures must match before approval. For AdaEvolve and
  EvoX, also run 3 iterations twice and compare every solution prompt, because the mode is drawn on every iteration.
- v3 finalize does not reuse the v2 mode-label admission (`sort_finalize.admit_prompt_mismatch`). With a seeded RNG,
  any mismatch excludes the run.

### 3.2 GEPA over many instances (item 2)

`_gepa_worker_v3(args)`:

- `dataset = valset = [{"id": iid} for iid in instances]` (30 items). Train equal to val is GEPA's multi-task mode.
  That is acceptable here because the holdout tests generalization. It is not TRACE-AUDIT defect 11, where train
  contained the val parents.
- `EngineConfig(seed=S, max_candidate_proposals=200, max_metric_calls=30 + 201*(2*3 + 30) = 7266,
  candidate_selection_strategy="pareto", frontier_type="instance", val_evaluation_policy="full_eval",
  acceptance_criterion="strict_improvement", cache_evaluation=True, cache_evaluation_storage="memory",
  parallel=False, max_workers=1, raise_on_exception=True)`. The value 36 per proposal comes from
  `lb.gepa_metric_calls_per_proposal(3, val)`.
- `ReflectionConfig(reflection_minibatch_size=3, batch_sampler="epoch_shuffled", module_selector="round_robin",
  reflection_lm=lm)`. `lm` is `SortBrokerLMv3` (the v2 client with the `SORT_PACKET_V2` marker), or
  `ReflectThenWriteLM` when routing is on (§3.6). Set `merge=None` and `refiner=None` explicitly.
- Pass `batch_evaluator=batch_eval` and no per-pair evaluator. `batch_eval(pairs)` groups pairs by candidate and
  POSTs `{"source", "instances": [ids]}` once per candidate to the verifier's `/evaluate_instances`. It returns
  `(instance_score, side_info)` in pair order.
- `instance_score(rows)` = `within/N + 0.25/(1 + mean_excess_valid) - invalid/N`, with the middle term 0 when no state
  is valid. This is the development formula without the worst-r term, which is undefined inside one r. Range
  [-1, 1.25]; the seed scores 0.53 to 1.17 per instance.
- `side_info` holds `instance`, `r`, `d_range`, `within`, `states`, `invalid`, `timeouts`, `mean_excess`,
  `seed_within`, `seed_mean_excess` and `feedback` (the instance packet, at most 2500 chars, §3.5).
- **Final pick.** GEPA's `best_idx` maximizes the mean instance score, which has no worst-r term. `_launch_v3`
  instead takes the argmax of full `combined_score` over the verifier's `full` rows. Every GEPA `full_eval` covers all
  30 instances, which is the full development set. Ties go to the lowest ordinal. GEPA's `best_idx` and its full
  score are recorded next to the pick.
- `SortVerifierV3.evaluate_instances(source, ids)` runs `E.evaluate` once per instance (50 states,
  `cache_dir` shared) in a `ThreadPoolExecutor(min(len(ids), jobs))`, with per-call
  `jobs=max(1, jobs // min(len(ids), jobs))`. The result cache is keyed on the instance's state set, so a parent's
  minibatch re-evaluation costs nothing. When `set(ids)` covers all 30 instances, it concatenates the rows and calls
  `E.aggregate(rows)`, then appends a `scope: "full"` row to the evaluation trace. That row drives best-so-far and
  `_finish`. Budgets are `max_state_evals` (states actually run; cache hits count 0) and `max_requests`, and
  exhausting either returns HTTP 429. `result-NNNN.json` gains `scope` and `instances`.

### 3.3 SkyDiscover Pareto objectives (item 3)

`_sky_evaluator_v3(stage, verifier_url, timeout, threshold)` writes `evaluator.py` with `evaluate_stage1`,
`evaluate_stage2`, and `evaluate` (which equals stage 2). Every metric is a float: no bools, no None.

- **Stage 2** (full, 1500 states): `combined_score` = full combined; `full_score` = the same value; `within_rate`;
  `worst_r_rate` = `min_r_within_rate`; `invalid_rate`; `stage = 2.0`; and `neg_mean_excess` = `-mean_excess`, or
  `-1000.0` when no state is valid. v2 mapped None to `-1.0`, which reads as better than an excess of 1.0; this fixes
  that bug.
- **Stage 1** (screen, 100 states): `combined_score` = screen combined, used only by `_passes_threshold`;
  `screen_score`, `screen_within_rate`, `screen_worst_r_rate`; `full_score = -2.0`, below the minimum real full score
  of -1; `stage = 1.0`. Stage 1 returns no Pareto keys, so its objective vector is `-inf`.
- **Failure** (HTTP error, timeout or 429): `full_score = -2.0`, `combined_score = -2.0`, `stage = 0.0`, and the
  artifact `feedback` "evaluation failed: ...". The stage functions never raise. Their HTTP timeout is
  `eval_timeout - 30`, so our sentinel returns before SkyDiscover's asyncio timeout fires. That timeout would produce
  `{"error": 0.0, "timeout": True}` and a proxy of 0.0.
- **Database config** for both `adaevolve` and `evox`:
  - `pareto_objectives`: `["within_rate", "worst_r_rate", "neg_mean_excess"]`
  - `higher_is_better`: `{"within_rate": true, "worst_r_rate": true, "neg_mean_excess": true, "full_score": true}`
  - `fitness_key`: `"full_score"`
  - `pareto_objectives_weight`: `0.0`, stated explicitly.
- The fitness key is `full_score` rather than `combined_score` because a program rejected at stage 1 carries the
  screen score in `combined_score`, which the threshold check needs. That score must never rank against full scores.
  Every result our evaluator returns has `full_score`, so the averaging fallback is reachable only through
  SkyDiscover's own exception paths. A smoke test greps the console for `Stage 1 failed` and `timed out`, and finalize
  flags any program record without `full_score`.

### 3.4 Cascade (item 4)

- `evaluator.cascade_evaluation = true` and `cascade_thresholds = [thr, thr]`; only index 0 is used in 0.2.0.
  `thr = campaign-config "screen_threshold" = 1.10`. For reference, the seed's screen score is 1.1887, the v2
  finalists score 1.46-1.65 and naive scores 0.06. Near-seed candidates that lose about 4 or more screen states on the
  worst r skip the full evaluation.
- `_setup_v3` evaluates the seed on the screen and on the full set without the cache (`cache_dir=None`). It aborts in
  any of these cases:
  - the seed's screen combined differs from `campaign-config "seed_screen_score"` by more than 1e-9 (1.1887 now;
    recompute it under Seatbelt before approval);
  - the seed's screen score is below `thr`;
  - the seed shows any TIMEOUT (it had 0 in v2).
- The verifier exposes `/evaluate` with `{"source", "scope": "screen" | "full"}` and separate `max_screen_evals` and
  `max_full_evals` budgets.
- GEPA does not use the SkyDiscover cascade. Its own cascade is the 3-instance minibatch (150 states) followed by a
  valset evaluation only on a strict minibatch improvement.
- Sequential uses the same screen gate (§3.9).

### 3.5 Rich feedback packet v2 (item 5)

These are search-side functions in `sort_loop3.py`. They use `sort_evaluator.Tables` read-only, and the evaluator
itself does not change.

- `optimal_word(tables, v)`: set `cur = v`; while `d(cur) > 0`, append the first `ch` in `"LRX"` with
  `d(replay_visible(cur, ch)) == d(cur) - 1`. It asserts `len == d(v)` and raises otherwise, because a mismatch means
  a table bug. L⁻¹ = R and X⁻¹ = X, so the Cayley graph is undirected and one letter changes d by at most 1.
- `divergence(tables, state, word)`: computes the d-trajectory and returns the first t with `d_t >= d_{t-1}`. This is
  the same as `Tables.prefix_trace`'s `first_off_shortest_path` (`t + d_t > d_0`). It returns t, `word[:t]`,
  `d_{t-1}`, `d_t` and `first_budget_lost`.
- `aligned_optimal(tables, v, word, t)` = `word[:t-1] + optimal_word(state after t-1 letters)`. This is an exact
  shortest word for v that follows the candidate for as long as the candidate stays optimal. It is the "BFS-optimal
  word backtracked from the table" that the packet shows.
- `packet_v2(result, rows, best_text, states_by_id, tables, seed_result, reveal) -> dict[str, str]` returns these
  artifact keys, each at most 2000 chars (§1 truncation):
  - `feedback`: marker `SORT_PACKET_V2`, scope (screen, full or instance), totals, worst r, timeouts, mean and max
    excess, combined, best so far, and two per-r lines built with `per_r_line` on the same scope: the candidate's
    and the seed's. It ends with the short structural facts.
  - `worst_states` and `worst_states_2`: up to 5 worst states in `sort_backends._worst` order. Each shows:
    - id, v, r, T, d, status and length;
    - the candidate's full word; above 160 letters it is shown as first 120 + "..." + last 30 + "(len N)";
    - the divergence step t with `d_{t-1} -> d_t`, and the step after which T is unreachable;
    - the aligned optimal word (at most 73 letters);
    - for NOT_SORTED, the final vector; for TIMEOUT or CANDIDATE_ERROR, the failure text (at most 160 chars) and
      `optimal_word(v)`.
  - GEPA gets one string per instance (at most 2500 chars) with the same content restricted to that instance, plus
    the seed's stats on that instance. Sequential gets all keys concatenated (at most 6000 chars).
- **Development only.** `tables_from_manifest` loads only the development (m, r) tables, and `guard_not_holdout` is
  unchanged. A test asserts that no holdout id or vector string ever appears in a packet.
- **Memorization control (new).** Exact optimal words for development states let a candidate hard-code them; 64 KiB
  of source fits several hundred. This is the verifier-exploit pattern. Four controls:
  1. `reveal_optimal_max_states` (config, 300 = 20% of development) caps the distinct states whose optimal word a run
     may reveal. After the cap, packets carry divergence data only.
  2. The verifier records the revealed ids in the manifest.
  3. Finalize reports each run's development within-rate on revealed and on never-revealed states, and flags a gap
     above 0.03.
  4. The holdout decides.

### 3.6 Model routing (item 6)

**Configuration**

- New `autoresearch/loop-v3-260925/broker-config-reflection.json` with these fields:
  - `model`: gemini-3.8-pro or grok-4.7, to be verified against a live model listing and current pricing before
    approval. That was not done here because it needs a live call.
  - `upstream_url` and `api_key_env` (`GEMINI_API_KEY` or `XAI_API_KEY`).
  - `ledger`: `autoresearch/loop-v3-260925/broker-ledger-v3-reflection.json`.
  - `max_tokens` 3000, `reasoning_effort`, `reasoning_cap_tokens`, the two prices, `max_prompt_bytes` 120000,
    `max_usd_per_run`, `timeout`.
- `campaign-config "reflection"`:
  `{"enabled": true, "broker_port": 8899, "max_requests": {"gepa": 215, "sequential": 215, "adaevolve": 20, "evox": 0},
  "diagnosis_max_chars": 4000, "on_failure": "halt"}`.

**Code in `sort_loop3.py`**

- `DiagnosisLM(ob.BrokerLM)`: its `_preflight` accepts any non-empty text that was not truncated. It strips fenced
  code, because a diagnosis may not carry code, and truncates to `diagnosis_max_chars`. System text `REFLECT_SYSTEM`:
  "Diagnose why the program fails on the listed states and propose concrete changes. Do not write code."
- `ReflectThenWriteLM.__call__(prompt)` makes two calls:
  1. `DiagnosisLM` on the reflection broker returns a diagnosis `d`.
  2. `SortBrokerLMv3` on the flash broker receives `prompt` + "Reviewer diagnosis (separate model; untrusted
     advice):\n" + `d`.

  It returns the flash content, and preflight is unchanged. Receipts cover both calls. GEPA uses it as
  `reflection_lm`, and sequential uses it when routing is on. HTTP 429 or 5xx from the reflection broker raises
  `BrokerHalted` and ends the run as BROKER_STOPPED. There is no silent fallback to flash-only, so the treatment stays
  uniform within a run.
- **Guard with routing.** Hash the first diagnosis request's messages, and the first write request's messages with
  the diagnosis text replaced by the literal `<DIAGNOSIS>`. Both hashes go into the per-(arm, seed) first-prompt files.
- **AdaEvolve.** `llm.guide_models = [{"name": <reflection model>, "api_base": "http://127.0.0.1:8899/v1",
  "api_key": "local-broker", "max_tokens": 3000, "timeout": ..., "retries": 0, "reasoning_effort": ...}]`. Paradigm
  calls go to the reflection broker, and solution proposals stay on `llm.models` (flash).
- **EvoX.** `guide_models` is not set and strategy evolution is off (§3.8), so 0 reflection calls are expected and no
  reflection broker is started.
- **`_live_v3`.** It starts the flash broker. When the arm's reflection cap is above 0, it also starts a second
  `research_budget serve` on `reflection.broker_port`, with ledger
  `broker-ledger-v3-reflection.{engine}.s{S}.json`, `--max-requests` set to the arm's cap and `--max-usd` set to that
  config's `max_usd_per_run`. The sandbox profile adds the reflection port to `loopback_ports`.
- **Asymmetry to report, not hide.** GEPA and sequential get a reflection call every iteration, AdaEvolve only at
  paradigm events (about 10 at most), and EvoX none. Finalize shows reflection calls and reflection USD per arm.
- Optional, human decision: add `"sequential_refinement"` and `"reflection_diagnosis"` to
  `research_budget._CALL_ROLES`. The sequential role is logged as `unknown` today. It is not required, because each
  ledger file already attributes the calls, and it is not planned by default because that file is money code.

### 3.7 200 iterations per arm (item 7)

In `campaign-config "engines"`, every limit applies to one run, meaning one (arm, seed):

| Arm | Iterations | Eval budgets | Flash `max_requests` | Wall s |
|---|---:|---|---:|---:|
| gepa | 200 proposals | `max_metric_calls` 7266, `max_state_evals` 380000 | 215 | 28800 |
| sequential | 200 | screen 205, full 205 | 215 | 28800 |
| adaevolve | 200 | screen 230, full 230 | 215 | 28800 |
| evox | 200 | screen 230, full 230 | 215 | 28800 |

A screen evaluation costs about 1/15 of a full one: 100 states instead of 1500, though the screen is weighted
toward hard states. Cost and wall time are in §4.

### 3.8 inject_evaluator_context and EvoX strategy generation (item 8)

- `_sky_config_v3` sets `evaluator.inject_evaluator_context = false` explicitly, not the auto `None`.
- `campaign-config "evox_strategy_evolution": false` is the only accepted value, and `_live_v3` refuses `true`.
  `_sky_config_v3` sets `search.switch_interval = iterations + 1` and
  `search.database.auto_generate_variation_operators = false` whatever the iteration count, and never calls
  `lb.evox_strategy_evolution_enabled`, which would return True at 200 iterations. `share_llm` stays true, as in v2,
  so any stray meta call hits the metered flash broker and is counted.
- `_launch_v3` checks EvoX after the run. It requires
  `ob._evox_meta_search_share(ledger)["evox_meta_search_calls"] == 0` and no `search/iteration_*/code.py`. Otherwise
  the status is `STRATEGY_EVOLUTION_LEAK` and finalize excludes the run.
- Note text for the config and the report: "EvoX's outer loop writes and runs LLM-generated Python search strategies.
  AGENTS.md forbids executing generated code outside the evaluator sandbox, so it is disabled in every run. The EvoX
  arm is EvoX's solution-level search only."
- AdaEvolve paradigm prompts contain the staged `evaluator.py` source regardless of the flag (§1). The stub must hold
  only the HTTP call. Its text sits inside `sort_loop3.py`, so the approval hash covers it. `use_paradigm_breakthrough:
  true` is set explicitly so the knob shows up in the hashed config.

### 3.9 Sequential control with the same packet (item 9)

`_sequential_v3(args)`:

- The prompt is `OBJECTIVE`, `lb.rejection_note(history)`, the current program, and "Evaluator feedback:" followed by
  the current best's full `packet_v2` string. When routing is on, the call goes through `ReflectThenWriteLM`.
- Screen first. A screen combined below `thr` is rejected. The history line then reads
  "screen {x:.4f} < threshold {thr}" plus the screen packet's first worst-state line (at most 300 chars), so
  consecutive prompts differ. Otherwise the candidate gets a full evaluation and is accepted if its full combined
  score beats the best full score so far.
- The v2 guards stay: the first-prompt check (with the diagnosis placeholder) and the refusal to resend an identical
  consecutive prompt. The iteration count (200) and caps match the other arms.

### 3.10 Approval hash (item 10)

`approval_material_v3(campaign_dir)` produces canonical JSON (`lb._canonical`), and the approval hash is its sha256.
`check_approval_v3` compares it with `campaign_dir/payload-approved.sha256`, which only a human creates. Like
`lb.check_approval`, it also checks `dry_run_payload_sha256` in both broker configs; `sort_backends.check_approval`
skipped that check.

**Covered:**

- `broker_config` (flash), `reflection_broker_config` and `campaign_config` as whole files, including every knob and
  every note.
- `engine_knobs`: `{f"{engine}/s{seed}": engine_knobs(cc, engine, seed)}` for all 12 runs, which are the exact GEPA
  `EngineConfig`/`ReflectionConfig` fields and the SkyDiscover config. Paths are replaced by `<STAGE>` and `<RUN>`.
- First-prompt hashes: 12 solution prompts and 6 diagnosis prompts (GEPA and sequential, 3 seeds each).
- The upstream endpoints and dry-run payloads of both brokers.
- Prompts: `SYSTEM` and `OBJECTIVE` (from `sort_backends`), `REFLECT_SYSTEM`, the diagnosis-append text, and the
  rendered sky evaluator stub source for `thr`.
- The packet format: marker `SORT_PACKET_V2`, the keys and their caps, 5 worst states, the word elision rule,
  "optimal words: development only", and `reveal_optimal_max_states`.
- The `instance_score` formula text, `screen_threshold` and `seed_screen_score`.
- Data: seed sha, v2 frozen manifest sha, development sha, frozen-v3 manifest sha, instances sha and screen-ids sha.
- The evaluator: `{VERSION, CONTRACT, evaluator_hash()}`, which covers `sort_evaluator.py`, `sort_worker.py`,
  `program_sandbox.py` and `certificates.py`.
- Code sha256 of `sort_loop3.py`, `sort_backends.py`, `lift_backends.py`, `official_backends.py` and
  `research_budget.py`. The last one is new: v2 did not cover the broker code that enforces money.
- The engines:
  - GEPA version plus the sha of `gepa/optimize_anything.py`, `adapters/optimize_anything_adapter/optimize_anything_adapter.py`
    and `proposer/reflective_mutation/reflection_lm.py`;
  - SkyDiscover version plus the sha of `optimize/config.py`, `evaluation/evaluator.py`, `utils/metrics.py`,
    `utils/pareto.py`, `search/base_database.py`, `search/adaevolve/database.py`, `search/adaevolve/controller.py`,
    `context_builder/adaevolve/builder.py` and `context_builder/utils.py` (the behaviors §1 relies on);
  - the interpreter path and version of `.venv-official`.

**Not covered, by design:** run outputs, ledgers and receipts, timestamps, the evaluation cache, tests, and
`sort_loop3_finalize.py`, whose sha is written into `finalists/manifest.json` before the holdout pass.

**What changes the hash:**

- any byte of a listed file, including notes in the configs;
- a first-prompt re-capture with a different result;
- a new threshold, seed list, reveal cap or iteration count;
- a rebuilt instance or screen file;
- a package reinstall that alters a listed file, or a different interpreter.

Any edit to `sort_backends.py` changes the v3 hash, because v3 imports it, and it also breaks v2's `7626d6b0`.

### 3.11 Campaign runner and finalize (item 11)

- `run-one.sh ENGINE SEED` runs `check-approval`, then `exec python -m integrations.sort_loop3 live --engine $1
  --seed $2`.
- `run-campaign.sh` loops over seeds 1, 2, 3 and, inside each, over gepa, sequential, adaevolve and evox. Runs are
  interleaved by seed, so an early stop leaves whole seeds rather than a missing arm. Runs are serial by default, with
  at most 2 at once (§5).
  - Before each run, `python -m integrations.sort_loop3 campaign-spend` sums `charged_usd` over every v3 ledger (flash
    and reflection). If that sum plus this run's `max_usd_per_run` for both brokers exceeds `cc.campaign_max_usd`, the
    campaign stops.
  - The campaign also stops after 2 runs end BROKER_STOPPED or INCOMPLETE. It then runs finalize.
- **Per-run caps replace the shared pool.** `_live_v3` gives each run's brokers `cc.engines[arm].max_requests` and
  `max_usd_per_run`. v2 passed the whole campaign `max_usd` to each arm's broker, which only the request sub-cap
  bounded.
- Ledger names: `broker-ledger-v3.{engine}.s{S}.json` and `broker-ledger-v3-reflection.{engine}.s{S}.json`.

**`integrations/sort_loop3_finalize.py`**

- **Finalists.** One per (arm, seed): the verified best of each `live-v3-*` run with status COMPLETE, chosen by full
  development combined score. It never selects by holdout and never takes the best of the seeds. Runs that ended
  FIRST_PROMPT_MISMATCH, STRATEGY_EVOLUTION_LEAK, INCOMPLETE or BROKER_STOPPED are listed as excluded, and n is
  reported per arm.
- **Freeze.** Copy the sources and write the manifest (hashes, finalize sha) before the holdout. Each finalist is
  evaluated on the holdout once, following the `sort_finalize` pattern: the results file is written once, then reused
  and hash-checked. The naive and sweep controls are also evaluated once. `sort_audit.audit` runs unchanged on
  development and holdout.
- **Report.** Per arm, over seeds: n, mean, sample SD, min and max of:
  - holdout within /2100, holdout worst-r rate, holdout (9,6) /300, holdout (10,3) /300, holdout mean excess;
  - development within /1500 and development combined;
  - flash and reflection USD, calls, truncations, accepted proposals;
  - the memorization gap.

  It also lists per-seed paired differences against sequential (arm minus sequential), without tests, and shows the
  v2 single-seed values in a reference row. Wording stays descriptive with n=3. The strongest allowed claim is
  "consistent in 3 of 3 seeds", never significance.

## 4. Cost and wall-time estimates (no live call made)

- **Flash.** v2 spent $4.58 over 218 calls, about $0.021 per call. v3 packets are larger (up to about 6k chars
  instead of 2k, and GEPA shows 3 instance packets), so assume $0.025-0.035 per call. 12 runs of about 205 calls is
  about 2,460 calls, or **$60-85**.
- **Reflection.** At most 3 x (200 + 200 + 20) = 1,260 calls. The price is unknown until the model is verified.
  Assuming a pro-class $2/M input and $12/M output, 15k input tokens and at most 3k output plus reasoning, a call costs
  about $0.07-0.10, so **$90-125**.
- **Total $150-210**, about 8-10 times all spend to date (about $20).
- **Cheaper options.**
  1. A pilot first: seed 1, 4 arms, 40 iterations, reflection on, about $8-12. It checks cascade pass rates, instance
     signal and whether proposals use the packet.
  2. A `reflect_every: 4` knob, which cuts reflection cost about 4 times.
  3. 100 iterations instead of 200.
- **Wall time.** A SkyDiscover iteration takes the LLM call (40-90 s), the screen (1-3 s), and the full evaluation
  (10-45 s) times the pass rate, so a run takes 3-5 h. GEPA and sequential with reflection take 5-8 h. The 12 runs
  take 50-70 h serially, or 25-35 h two at a time.

## 5. Tests and verification (offline; mock HTTP only)

`tests/test_search_sort_loop3.py`:

1. Instances: 30 x 50 partition the development set; the screen has 100 states, is a subset of development, and
   includes all 15 radius states; both hashes are deterministic.
2. `instance_score`, including the no-valid-state case. `E.aggregate` over the union of instance rows equals
   `E.evaluate` on the full set (`process_only` on a small synthetic set).
3. `engine_knobs`:
   - per-seed `random_seed` for AdaEvolve and EvoX, and the GEPA seed;
   - `frontier_type="instance"` and minibatch 3;
   - `inject_evaluator_context` false, cascade on with `[thr, thr]`;
   - EvoX `switch_interval = iterations + 1` and variation off at 200 iterations;
   - the Pareto objectives, `higher_is_better` and `fitness_key`.

   Parse the rendered config with SkyDiscover `Config.from_dict` from `.venv-official` (skip if absent) and assert the
   `guide_models` `api_base` is the reflection URL.
4. Sky stub: the stage-1, stage-2 and failure metric dicts are all floats, always include `full_score`, and use the
   `neg_mean_excess` sentinel; SkyDiscover's `compute_proxy_score` equals `full_score` for each (skip if the venv is
   absent).
5. `optimal_word` has length d and replays to the root on the existing exact-table fixture; the aligned word agrees
   with the prefix; `divergence` equals `prefix_trace` `first_off_shortest_path`.
6. `packet_v2`: key caps, 5 worst states, word elision, the seed's per-r line, no holdout id in any packet, and the
   reveal cap enforced and recorded.
7. `ReflectThenWriteLM` against two mock brokers: call order, code stripped from the diagnosis, placeholder hashing
   for the guard, and a reflection 429 raising `BrokerHalted`.
8. Verifier budgets: screen, full and state caps return 429; per-instance cache reuse; a full row is recorded only for
   the complete union.
9. Approval: changing any key of campaign-config, the reflection config, the instances, the screen or a first-prompt
   file changes the hash; `check_approval_v3` refuses; the `research_budget` sha is present.
10. EvoX leak detector: synthetic receipts containing a meta request give `STRATEGY_EVOLUTION_LEAK`.

`tests/test_search_sort_loop3_finalize.py`: synthetic run dirs (2 arms x 3 seeds) give per-arm mean, SD, min and max;
best-of-seeds is never used; each finalist's holdout is evaluated once; excluded runs are counted; the memorization
gap is computed.

**Smokes.** `smoke-{arm}-s1` through the extended mock with two ports, 3 iterations each, all COMPLETE. First prompts
captured twice per (arm, seed).

**Commands.** The three AGENTS.md commands, plus `python tools/orchestrator.py trusted` (must stay ok) and
`python -m integrations.sort_backends approval-hash` (must still print `7626d6b0...`).

## 6. Open decisions and risks

- **O1. Holdout.** Reusing the v2 holdout keeps the numbers comparable, but v2 results informed this design. A fresh
  disjoint draw from the existing (9, 1..6) and (10, 3) tables is cleaner and adds a `build_frozen` step.
- **O2. Reflection model.** Its identity and price need a live listing, which needs explicit authorization.
- **O3. Scale.** The full 3 x 4 x 200 campaign, or the pilot, `reflect_every` or 100-iteration variants (§4).
- **O4. AdaEvolve reflection.** Whether AdaEvolve's paradigm calls use the reflection model, given the per-arm
  asymmetry (§3.6).
- **O5. Broker roles.** Whether to add the two roles to `research_budget._CALL_ROLES`.
- **Risk: first-prompt determinism.** It depends on seeded RNGs and on the seed evaluation being identical. A TIMEOUT
  caused by load changes the packet and fails the guard. The setup check for seed TIMEOUTs (§3.4) and a cap of 2
  concurrent runs mitigate this.
- **Risk: load and the cache.** The 1 s per-state wall limit can turn machine load into TIMEOUTs, and TIMEOUT rows
  are cached (only `incomplete` results skip the cache). Keep total evaluation jobs at or below the physical core count
  minus 2.
- **Risk: overfitting.** With train equal to val over the development set, and optimal words revealed, dev overfitting
  is possible. The reveal cap, the memorization gap and the holdout guard against it.
- **Risk: instance saturation.** 18 of 30 instances are saturated on within for the seed; the excess term carries the
  Pareto signal. If GEPA's instance frontier stays flat in the pilot, reconsider the partition before the full
  campaign.
- **Risk: version-specific behavior.** The proxy order, cascade merge and artifact truncation belong to SkyDiscover
  0.2.0. The package-file hashes in the approval material pin them.

## Appendix A. Draft `campaign-config.json` (values to be confirmed before approval)

```json
{
 "campaign": "loop-v3-260925",
 "seed_program": "integrations/sort_control_sweep.py",
 "frozen_manifest": "autoresearch/sort-m9-260925/frozen/manifest.json",
 "frozen_v3_manifest": "autoresearch/loop-v3-260925/frozen-v3/manifest.json",
 "python": ".venv-official/bin/python",
 "eval_cache": "autoresearch/loop-v3-260925/eval-cache",
 "broker_port": 8898,
 "eval_timeout": 900,
 "seeds": [1, 2, 3],
 "screen_threshold": 1.10,
 "seed_screen_score": 1.1887,
 "reveal_optimal_max_states": 300,
 "packet": {"marker": "SORT_PACKET_V2", "worst_states": 5, "key_max_chars": 2000, "instance_max_chars": 2500,
            "sequential_max_chars": 6000},
 "evox_strategy_evolution": false,
 "campaign_max_usd": null,
 "reflection": {"enabled": true, "broker_config": "broker-config-reflection.json", "broker_port": 8899,
                "max_requests": {"gepa": 215, "sequential": 215, "adaevolve": 20, "evox": 0},
                "diagnosis_max_chars": 4000, "on_failure": "halt"},
 "engines": {
  "gepa": {"iterations": 200, "max_metric_calls": 7266, "max_state_evals": 380000, "minibatch": 3,
           "frontier_type": "instance", "max_requests": 215, "wall_seconds": 28800},
  "sequential": {"iterations": 200, "max_screen_evals": 205, "max_full_evals": 205, "max_requests": 215,
                 "wall_seconds": 28800},
  "adaevolve": {"iterations": 200, "max_screen_evals": 230, "max_full_evals": 230, "max_requests": 215,
                "wall_seconds": 28800},
  "evox": {"iterations": 200, "max_screen_evals": 230, "max_full_evals": 230, "max_requests": 215,
           "wall_seconds": 28800}
 },
 "evox_note": "EvoX's outer loop writes and runs LLM-generated Python search strategies; AGENTS.md forbids executing generated code outside the evaluator sandbox, so it is disabled in every run (switch_interval = iterations + 1, variation operators off, post-run leak check).",
 "sky_note": "inject_evaluator_context is false. AdaEvolve paradigm prompts still include the staged evaluator stub source (SkyDiscover 0.2.0 adaevolve/controller.py:80-112); the stub holds only the HTTP call."
}
```

`campaign_max_usd` is null until O2 and O3 are decided, and `_live_v3` refuses to start while it is null. The flash
`broker-config.json` is the v2 file with ledger `broker-ledger-v3.json` and `max_usd_per_run` in place of the pool
fields. `contact_ceiling_*` and `max_requests` are removed because the per-run caps above replace them.
