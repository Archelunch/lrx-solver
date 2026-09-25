# Trace audit: lift-m9-260924 and corr-cert-260924 (2026-09-25, read-only)

Method: every broker receipt assigned to an arm by request time (arm dir name = UTC+2). lift: 264 receipts in broker-ledger-gemini.json.receipts; corr: 147 in broker-ledger-corr-8k.json.receipts (the 17 in broker-ledger-corr.json belong to the superseded gepa-231758 arm). Responses re-classified with the repo's own `preflight_source` (lift_backends.py:130, corr_backends.py:166); diff arms parsed as SEARCH/REPLACE against the parent shown in the prompt (exact match, so "search miss" is an upper bound). Packets matched byte-exact against `verified/evaluations/result-*.json` feedback: every packet found in a prompt equals a verifier packet.

## 1. What the model received (avg over arm; representative attempts = first/middle/last)
| arm | calls | avg chars | program | packet | boilerplate+task | samples (attempt: chars prog%/pkt%) |
|---|---|---|---|---|---|---|
| lift gepa | 77 | 17.4k | 51% | 29% (3 packets) | 20% | 1: 13.0k 33/41; 39: 19.5k 58/25; 77: 20.0k 57/27 |
| lift seq | 60 | 9.3k | 65% | 19% | 16% | 78: 7.6k 57/24; 108: 7.9k 59/22; 137: 13.7k 76/13 |
| lift ada | 60 | 23.3k | 65% (2.7 copies) | 7% | 28% | 138: 14.6k 59/12; 168: 27.1k 70/7; 197: 25.1k 67/7 |
| lift evox | 67 (40 solution) | 18.7k | 43% | 6% | 51% | 198: "ping" 5 chars; 231: 21.1k 69/8; 264: 23.4k 62/8 |
| corr gepa | 31 | 18.6k | 39% | 32% (same packet x3) | 29% | 1: 13.3k 14/44; 16: 19.7k 42/30; 31: 18.8k 39/31 |
| corr seq | 60 | 9.3k | 37% | 21% | 42% | 32: 7.7k 25/25; 62: 10.5k 45/19; 91: 10.5k 45/19 |
| corr ada | 56 | 20.7k | 47% | 10% | 43% | 92: 11.6k 33/17; 120: 17.8k 41/11; 147: 22.0k 53/9 |
| corr evox | 0 | - | - | - | - | no call reached the provider (see defect 2) |
- Holdout/consumed data: never. 0 lift holdout parent ids, 0 non-development parent ids, 0 corr `m=13..20` strings in any of 411 prompts. Corr SYSTEM only names the holdout conceptually.
- Currency: lift GEPA packets say `best so far: screen 56.6166 (56/306 certificates); full development 285/4588` in all 231 packets (77 prompts x 3), i.e. the seed, while the verifier reached 64.6238/337. Cause: `LiftVerifier.evaluate` updates `best_screen` only when `parent_id is None`; GEPA only sends parent-scoped evals. Seq packets are current (5 distinct values, advance on each accept). Ada/EvoX packets are the parent's artifact frozen at its eval time; corr ada prompts said `best so far ... 134467` in 47 prompts while better candidates existed (defect 1).
- Noise: AdaEvolve repeats the program 2-3x, adds "Solution is long (>500 chars); consider simplifying" and SkyDiscover's sample diff "# Reorder loops for better memory access pattern". Seq sends 1 packet; GEPA 3.

## 2. What the model returned (every response)
| arm | valid | truncated | format (prose/multi/none) | diff fmt fail | diff search miss | syntax | other | identical to parent |
|---|---|---|---|---|---|---|---|---|
| lift gepa 77 | 51 | 25 | 0 | - | - | 1 | - | 0 |
| lift seq 60 | 16 | 8 | 36/0/0 | - | - | 0 | - | 0 |
| lift ada 60 | 22 | 18 | - | 2 | 11 | 0 | 7 meta ok | 0 |
| lift evox 67 | 10 | 24 | - | 2 | 4 | 0 | 25 meta ok, 2 meta trunc | 0 |
| corr gepa 31 | 30 | 1 | 0 | - | - | 0 | - | 0 |
| corr seq 60 | 1 | 14 | 37/4/2 | - | - | 0 | 2 content_filter | 0 |
| corr ada 56 | 22 | 25 | - | 1 | 1 | 0 | 7 meta ok | 0 |
- Truncations are visible output hitting max_tokens (median 4037-4091 completion tokens lift, 8188 corr), not hidden reasoning; only lift seq shows ~3.9k hidden tokens in 4 of 8.
- Corr seq 59/60 invalid (manifest: 45 "only one fenced Python source block", 14 truncated): 37 prose before the block, 4 multiple fences, 2 empty/no fence, 2 `content_filter: OTHER` (reported as fence errors), 14 length. All 41 prose/multi-fence responses contain a last block that defines `coefficients` and parses. Examples: attempt 33 starts `"An exact certificate requires satisfying the linear potential / pair / triple inequalities.\nNotice that the prompt explicitly states:..."` then one block (13.1k chars); attempt 32 has 10 fences, including a scratch `m = 4\nQ = 1\n# lambda:` block before the real one.
- Lift GEPA vs seed (14 accepted candidates, AST diff ignoring docstrings): all 14 touch word construction (`_pair_word` 14, `_reduce` 14, `gadget`/`_build_gadget` 14, `_lifted` 5) and `lift`; 11 of 14 add a scoring/selection helper (`_eval_slopes_and_base`, `compute_metrics`, `_solve_lp_gap` which is `pass`, `_solve_approx_lp`). All 51 valid GEPA proposals vs their shown parent: 47 construction, 4 selection-only. "Construction" here is mostly enumerating the seed's own knobs (bubble/head/align direction, alternative 4-letter transpositions) plus `XX` cancellation.

## 3. Feedback influence (5 consecutive iterations)
- Lift GEPA attempts 11-15: 24/24/21/18/18 packet items (parent ids, slope fractions like `'57/8'`, `need base<95`, word prefixes); references in response = 0/0/0/0/0. Lift seq 114-118: 0 of 4 each.
- Corr GEPA attempts 11-15: 1/8/10/8/3 of 20 items. The model fits packet kappa values in comments, e.g. `# m=6, (1,2) g=1, q=5 -> -44` and `# m=8: (2,3) at q=7 is -120. (3,4) at q=7 is -152. Diff = -32 = -4 * 8.`

## 4. Plateaus and best mechanisms
- lift gepa: best (screen 64.6238, full 336) at LLM call 36/77; nothing after for 41 calls. Almost all gain came from candidate 1 (val 4.669 -> 5.2557 of final 5.2585). Mechanism: enumerate 25 configs (bubble/head/align direction x 7 swap-transposition patterns) per parent row, drop words that do not sort, rank per row by a self-made proxy (word length as "base", X-hits at zero positions as "slopes", not Lemma 1), brute-force parent-weighted combos on the proxy, fill to 16 words round-robin; the evaluator's exact LP then weights them.
- lift seq: step 1 took screen 56 -> 64 certs; steps 37/49/55/57 changed only gap_sum decimals; best full 337 at step 37, 334 for the verified screen-best. Mechanism: pair m+1 with anchor labels m, 1, m-1, 2 (not only m), with inversion and 3x3x3 direction variants, up to 120 sorting words, pick 16 with its own LP heuristic.
- lift ada: last new best iteration 27/50 (call ~33/60); 64.6234 screen, 337 full. Mechanism: iterative LR/RL/XX reduction; both pair orders (m,m+1)/(m+1,m); head/move/align in {short,L,R}; one word per row, then fill to 16.
- lift evox: new bests at iterations 1, 3, 13, 40; 64.6239/337, but only 10 of 40 iterations produced a program. Mechanism: 8 fixed CONFIGS (direction x alternate head x alternate align), per-row sort by word length, round-robin to 16.
- All lift arms sit at 64/306 screen certificates after the first 1-3 accepted proposals; the rest is 4th-decimal gap_sum.
- corr gepa: still improving at call 29/31 (violation 11059 -> 26183/3) when GEPA's metric budget ran out. Mechanism: hard-coded m=4 and m=5 certificates from the prompt, else linear alpha/beta/gamma potentials anchored at reversal rows.
- corr seq: single accept at step 27. corr ada: last recorded best at iteration 4 (call 5/56); true best was discarded (defect 1). Mechanism: m=4/5 hard-coded, else `mu_a(q)=4(q-(m-1-a))`, `lambda=-4(m-a)(m-b)`, zero triples.
- All three corr arms pass exactly m=4 and m=5, i.e. the two certificates printed verbatim in SYSTEM; no arm passes any m >= 6.

## 5. Engine-specific
- AdaEvolve: 1 of 53 lift and 1 of 49 corr solution prompts had no packet (seed parent with no artifact yet); 3 lift and 1 corr prompts used a parent with 0 valid instances; no migrations logged (2 islands, `migrat` count 0); 7 paradigm calls per campaign, with packets.
- EvoX lift: 27/67 calls (40%) were meta (8 strategy-code, 7 attempt summaries, 8 population summaries, 2 `ping`, 2 guidance/context). 7 strategies were generated and none was adopted (`is_new_best: false` in all 7 `search/iteration_*/metadata.json`; window gains 0.0065, 0, 0, 0, 0, 0, 0.0019). One crashed: `'EvolvedProgramDatabase' object has no attribute 'best_program'`. Strategy 1 ("stagnation-aware parent & context selection") changed only parent/context sampling.
- EvoX corr: 40 iterations failed in one second with `429 shared upstream request cap reached`, meta-LLM "not reachable", 0 provider calls.
- GEPA lift: minibatch 3 (default) from train=210 parents vs valset 14; train includes all 14 valset parents, 12 of them sampled. 60 distinct minibatches over 180 parents, so parents rotate. Only 12 distinct parent programs were shown across 77 prompts, and 17 prompts were byte-identical retries after truncation/syntax failure.
- GEPA corr: train = val = 1 example, but minibatch defaults to 3, so the same packet appears 3x per prompt and each proposal costs 7 metric calls vs `per_proposal = 3` assumed; `max_metric_calls=184` ran out after 31 of 60 proposals. Only 6 distinct prompts in 31 calls (one sent 16 times); 24 identical resends after a valid-but-rejected child.

## 6. Defects, ranked by impact (one-line fix each)
1. Corr SkyDiscover evaluator does `float(out['violation_sum'])` on rational strings (`'56934268/3465'`); 5 valid candidates became failures, including the ada arm's best (violation 16431 vs recorded 134467). Fix: `float(Fraction(...))` in `_sky_evaluator` for corr.
2. One 147-request cap shared by all corr arms; gepa+seq+ada used 31+60+56=147, so EvoX got 0 calls and is reported `NO_VALID_PROPOSAL`. Only $3.25 of $24.64 was spent. Fix: per-arm request sub-caps, or abort the campaign before an arm starts with no headroom.
3. Strict preflight rejects any prose outside the block: 36 lift-seq and 41 corr-seq responses held a parseable program. Fix: accept the last fenced block that defines the entry function, and copy GEPA's "Provide ONLY ... within ``` blocks" line into the seq prompt.
4. Sequential loop resends the identical prompt after a rejection (lift 6 distinct prompts in 60, corr 2 in 60) with no reason given. Fix: append the last outcome (invalid reason or rejected packet) to the next prompt.
5. Corr GEPA minibatch 3 over a 1-example dataset: triplicated packet (~4k chars per prompt), 7 calls per proposal, 29 proposals lost, 25/31 prompts identical. Fix: `reflection_minibatch_size=1` and `per_proposal=7` or single-instance mode.
6. Output caps: 25/77 lift-GEPA, 18/60 lift-ada, 24/67 lift-evox, 25/56 corr-ada responses truncated; about $1.5 spent on truncated output. Fix: lift max_tokens 8192 and a "no prose, no docstring" instruction; for diff arms, ask for diffs only.
7. Lift GEPA packets report seed best (56.6166/285) for the whole run. Fix: update `best_screen`/`best_full` from parent-scoped evals, or drop the best line when scope is not screen.
8. Corr score floor: m=4/5 certificates are in SYSTEM, so every arm gets 2/9 and `research_status: NEW_CERTIFICATES` for copying the prompt. Fix: score only m >= 6, or mark prompt-given m as known in the status.
9. EvoX on short runs: 40% of calls on meta-search with no adopted strategy and one crash. Fix: disable strategy evolution below about 100 iterations.
10. AdaEvolve prompts: 2.7 program copies plus generic hints (65% program, 7% packet). Fix: `num_context_programs: 0` or 1 and a custom template that removes the sample diff.
11. Lift GEPA trainset contains the 14 valset parents. Fix: train = development minus screen parents.
