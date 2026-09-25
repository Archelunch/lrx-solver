# Track 2: bounded-construction task (bound-m-260925)

Date 2026-09-25. This is a design contract only. No code, sets, controls or approval
material exist yet. No provider call is authorized. The rationale, the calibration and
the build plan are in `SPEC-track2.md` in this directory.

The main conjecture E_r(n) <= T_m(n) is open. Lemma 1, formulas (4)-(5) and criterion (7)
are the research group's (m=8 manuscript, replicated in `autoresearch/verify-m8-260924/`).
Here they are applied with m as a parameter. A certificate proves a bound only for its
own family. A miss, crash or timeout proves nothing.

## Goal

We want a program `certify(family)` that works for any m (no m-specific tables). For every
family it returns sorting words whose Lemma-1 affine costs certify the family: every state
of the family, at every block length, gets d(v) <= T_m(n). The score is a proof-shaped
bound. Certified means the bound is exactly T_m(n). Otherwise the exact excess over T is
reported per family.

## Family (m in {9,10,11})

- `labels` a is a permutation of 1..m. `mask` S has bits 0..m, and bit g means linear gap g
  is nonempty. Gap g lies before label a_{g+1}; g = 0 is the leading gap and g = m the
  trailing gap. S != 0, and k = popcount(S) is the number of zero blocks.
- Blocks are numbered j = 0..k-1 by increasing gap, so `gaps = [g_0 < ... < g_{k-1}]`.
- The unit base is `lrx_m.base_vector(a, S)`: one zero in every gap of S, n = m+k, r = k.
- The family covers the states V(a,S,l) with l_j >= 1 zeros in block j. Here
  r = sum l_j = k + sum z_j with z_j = l_j - 1 >= 0. Every visible vector with labels 1..m
  and r >= 1 zeros lies in exactly one family.
- Budget: T = T_m(m+k) = m(m+1)/2 + (k-1)(m-2). Slope bound s = m-2 = T_m(n+1) - T_m(n).
  For m = 9, 10, 11 this gives T = 38+7k, 47+8k, 57+9k and s = 7, 8, 9.

## Lemma 1 lift macros and cost (exact rules, m-independent)

These rules are implemented as `integrations/lrx_m.Profile` (unchanged). The word acts on
the unit base with a cursor c over fixed cells: L moves c+1, R moves c-1 (mod n), and X
swaps cells c and c+1. The run keeps rotation counters d and cz_j and closes a segment at
every X.

| letter, cells (c, c+1) | unit effect | stretched macro (block j has 1+z_j zeros) | counters |
|---|---|---|---|
| L over label | c+1 | L | d += 1 |
| L over zero Z_j | c+1 | L^{1+z_j} | d += 1, cz_j += 1 |
| R onto label / onto Z_j | c-1 | R / R^{1+z_j} | d -= 1 (and cz_j -= 1) |
| X (label, label) | swap | X | q += 1 |
| X (Z_j, label) | swap | L^{z_j} X (RX)^{z_j} | cz_j += 1 before closing, A_j += 1, q += 1 |
| X (label, Z_j) | swap | X (LX)^{z_j} R^{z_j} | A_j += 1, q += 1, next segment starts cz_j = -1 |
| X (zero, zero) | - | forbidden, word INVALID | - |

With segments s = (d_s, cz_s), the lifted word W(z) is prod_s rot(d_s + cz_s . z) core_s, and

    |W(z)| = q + 2 sum_j A_j z_j + sum_s |d_s + cz_s . z|
          <= B + sum_j beta_j z_j,   B = q + sum_s |d_s|,   beta_j = 2 A_j + sum_s |cz_{s,j}|.

Equality holds when each segment's nonzero coefficients share a sign. The upper bound
always holds by the triangle inequality, so the certificate does not need the same-sign
condition. The block at gap 0 and the block at gap m are separate atoms. An X at c = n-1
between them is a zero-zero swap and is rejected.

## Criterion (7), m-parametric, and the gap

Let a word set have unit costs (B_i, beta_i), and let w be rational with w >= 0 and
sum w = 1. Write Bbar = sum w_i B_i and betabar_j = sum w_i beta_{i,j}.

**Certified** if and only if an LP optimum w has Bbar < T + 1 and betabar_j <= s for all j.
Then for every z >= 0: min_i |W_i(z)| <= Bbar + betabar.z < T + 1 + s sum z = T_m(n) + 1.
So d(v) <= T_m(n) for every state of the family. The evaluator solves the exact rational
LP `lift_evaluator.mixture_lp`. Candidate weights are only checked and reported.

**Gap** (search signal for a valid family that is not certified). This is
`lift_evaluator.gap_lp` with bound s and strict = T+1:

    g = min_w  max(0, Bbar - (T+1)) + max(0, max_j betabar_j - s)

g never grows when words are added. Certified implies g = 0. The converse fails at one
boundary: the best mixture reaches Bbar = T+1 exactly with the slopes within bound. That
family has g = 0 and status `BOUNDARY`. It is not certified, and its bound is T_m(n)+1.
The scratch probes met this 3 times in about 250 families. `certified iff g == 0` is
therefore false, and the scorer uses the status, never g, to count certificates.

**Bound statement** (reported for every valid family). Take the gap-LP mixture, with
t = max(0, max_j betabar_j - s). Then for all states of the family,

    d(v) <= T_m(n) + floor((Bbar - T) + t (r - k)).

Certified families state this with t = 0 and Bbar - T < 1.

## Candidate

A stdlib Python program, at most 64 KiB, with `certify(family: dict) -> dict`. It runs only
in the existing Seatbelt sandbox path (`program_sandbox`, `_preexec`), one process per
family (BATCH = 1 since bound-eval-2; it was 4). Each family gets 3 s CPU (ITIMER_PROF) and
5 s wall. The kernel RLIMIT_CPU bounds the process, as in `sort_worker`. The candidate shares
the worker process, so the worker's per-family times are only reports: the parent reads the
process CPU from `os.wait4` and marks the family INCOMPLETE (timeout) when that exceeds
3 s + 2 s import/startup, or exceeds the reported time by more than the 2 s allowance. So a
candidate that disarms the alarms gains at most 2 s of CPU per family, and cannot pool CPU
across families. Fork is denied (Seatbelt `deny process-fork`
and RLIMIT_NPROC 1), so the per-process CPU cap covers all candidate work.

Input:
```json
{"id": "m10-mask1234-labels10.9.8.7.6.5.4.3.2.1", "m": 10, "labels": [...], "mask": 1234,
 "gaps": [1, 4, 6, 7, 10], "k": 5, "unit_base": [...], "budget_unit": 87, "slope_bound": 8}
```
Output: `{"words": [...], "weights": [...]?, "note": "..."?}`. Rules:
- 1..32 words, each over L, R, X, at most 4000 letters.
- `weights` is optional, one per word: a string `p` or `p/q` (at most 40 digits each) or an
  int below 10**40, forming a probability vector. The format is checked before any Fraction
  is built, so a string like `1e10000000` cannot stall the trusted parent.
- `note` is cut at 500 characters.

The family is **INVALID_OUTPUT** if any word fails any of these checks:
- it sorts the unit base to the root with no zero-zero swap (`Profile`);
- it passes literal lifted execution at z = 0, e_j, 2e_j, e_j+e_{j+1} for all j, and (1,...,1);
- its lifted length equals F(z) and is at most B + beta.z.

Output is never repaired.

Preflight also rejects a source that contains a string constant, or a concatenation of string
constants (`a + b`, `'sep'.join([...])`), of at least 24 characters that is at least 90%
L/R/X/l/r/x; more than 512 characters of such strings in total; more than 4096 characters of
string constants outside docstrings; a literal container with more than 64 elements, or more
than 256 constant elements across all literal containers; an int constant of 10**40 or more;
or a bytes constant larger than 256 bytes. This is a screen against tables, not a guarantee
(an encoded table can still get through). The real uniformity test is m=11, which is entirely
unseen.

## Score

For each family the scorer records a status. The status is one of CERTIFIED, BOUNDARY,
NO_CERTIFICATE, INVALID_OUTPUT or INCOMPLETE. INCOMPLETE covers a timeout, a crash or a
worker failure. It is never read as "no certificate exists". The scorer also records g, the
bound statement and the packet data. Invalid and INCOMPLETE families get g = 4000.

For each m:
- `pct_m` = 100 C_m / N_m, where C_m is the number of certified families. This is the primary score.
- `W_m` = max g over all N_m families. This is the bound, and it is `complete` only when every family is valid.
- `G_m` = mean g over the valid families.

The development set has M = {9, 10}:

    combined = mean_m pct_m + min_m pct_m + 0.06 V/N + 0.06/(1 + max_m W_m) + 0.03/(1 + mean_m G_m)

V is the number of valid families. The secondary terms sum to less than 0.15. One certificate
is worth at least 0.2, so certificates dominate lexicographically. The worst m is counted
twice. GEPA's per-example metric is 1 for CERTIFIED, 0.5/(1+g) for a valid family that is not
certified, and 0 otherwise. Finalists are ranked by `combined` on the full development set.
The holdout is reported as the tuple (C_m per m, W_m, G_m, invalid, timeouts). A combined
value is given too, but it is not used to rank.

## Sets (built by `build_frozen.py` from the definitions, stdlib `random`)

| set | m | per k stratum | strata | families | seed |
|---|---|---|---|---|---|
| development | 9 | 17 | k = 2..10 | 153 | 2609251 |
| development | 10 | 15 | k = 2..11 | 150 | 2609251 |
| holdout | 9 | 17 | k = 2..10 | 153 | 2609252 |
| holdout | 10 | 15 | k = 2..11 | 150 | 2609252 |
| holdout | 11 | 15 | k = 2..12 | 165 | 2609253 |
| edge (diagnostic, unscored) | 9, 10 | k = 1 | 1 | 10 + 10 | 2609254 |

- **Order classes in each k stratum.** For m = 9 the counts are 5/3/2/3/3/1, and for
  m = 10, 11 they are 4/3/2/3/2/1:
  - rev_rot: the reversal (m..1) and its cyclic rotations;
  - near_rev: the reversal with one adjacent transposition, then a random rotation;
  - refl: (2,1,m,...,3) and its rotations;
  - high_inv: uniform orders with inv >= ceil(0.75 C(m,2)), by rejection;
  - uniform;
  - easy: an identity rotation or inv <= 0.25 C(m,2).
- **Masks.** Each mask is a uniform k-subset of {0..m}. Every stratum with k >= 2 contains at
  least one mask with bits 0 and m both set, and at least one with neither.
- **Tight stratum (development m=9).** These families contain a state at exactly T_9(n).
  They come from `argmax_cls` in `outer-layer-260925/class_m9_r{1..5}_full.json`. The families
  with k >= 2 are (a,S) = (2,1,7,9,8,6,5,4,3){2,3}, (2,1,9,...,3){2,6}, (2,1,9,...,3){1,2,5},
  (4,3,2,1,9,...,5){4,8}, (5,4,3,2,1,9,...,6){0,5}, (7,6,...,1,9,8){2,7} and (9..1){0,4}. They
  take high_inv or uniform slots in their k stratum. The k = 1 tight families (2,1,9,...,3){2},
  (9..1){0}, (4,1,3,2,9,...,5){4}, (2,3,1,9,...,4){3} and (3,2,1,8,9,7,...,4){3} go to the edge
  set. For m = 10 the builder takes the (10,3) states with d = T from `sort-m9-260925/frozen/holdout.json`
  when they are present, and records any that are missing.
- **Disjointness and hashes.** Development, holdout and edge are disjoint on (labels, mask).
  The manifest records the seed, every family's class, inv, k and mask flags, the file sha256
  values, and the reversed-direction check that every unit base rebuilds.
- **Holdout protocol.** The holdout is frozen and hashed before any live call. m=11 appears
  in no prompt, packet or trainset. The holdout is evaluated once, after finalist freeze, by
  a human-run command.
- **Screen and trainset.** The screen is 30 development families (15 per m). Each has at
  least one family per k, and the rest are drawn from rev_rot, near_rev and tight. It is
  GEPA's valset and the selection score. The trainset is the development set minus the
  screen. A candidate that is valid on the whole screen and ties or beats the best screen
  score gets a full development evaluation.

## Controls (development and holdout, same evaluator)

- **(a) naive.** Bubble sort in the fixed frame (`sort_control_naive.sort_word` on the unit
  base). One word.
- **(b16) sweep-16.** Builds the pool of all cyclic-sweep variants of `sort_control_sweep`
  (target shift x zero assignment x mode L/R/greedy). It keeps the words that pass `Profile`
  and returns the 16 with the lowest (max slope, base). This is the campaign seed. It is
  cheap, and its selection leaves room for improvement.
- **(b) sweep-LP.** Uses the same pool with an exact LP over the whole pool and returns the
  support, which has at most k+1 words. This is the strongest deterministic reference, and
  it is trusted repository code (`--no-os-sandbox` is allowed). An engine claims progress
  only if it beats (b) on the holdout.
- **(c) sort-m9 program (m = 9, with m = 10 as a diagnostic).** The GEPA finalist
  `sort-m9-260925/finalists/sources/gepa.py` runs as `sort_word(unit_base)` under the
  existing Seatbelt `sort_worker` limits. Its one word is priced by Lemma 1. It is generated
  code and never runs in-process.

The comparison construction of Lemma 3 (reference Q, `lift_task.comparison_word`) is
optional as control (b'). It needs a reference per mask. The m-uniform choice is the sweep-LP
support on the reversed order with the same mask, transferred at an admissible cut when
P ⪯ Q.

## Packet (`BOUND_PACKET_V1`, at most 3000 characters, current best from every scope)

The packet has these parts:
- **Totals.** For each m: C/N, boundary, invalid, timeouts, W_m and G_m. For each (m,k):
  certified out of N. The best so far, recomputed from the evaluation manifest.
- **Failing families.** Up to 3. Worst g comes first. Ties go to smaller k, and the three
  should come from different order classes. Each failing family shows:
  - id, m, k, labels, mask, gaps, unit_base, T and s;
  - the gap-LP weights, Bbar against T+1, and betabar_j with (gap g_j, excess, tight at the
    optimum);
  - the lifted cost of each word, for the 6 words with the highest weight: length, B, the
    beta vector, the split beta_j = 2A_j + rotation passes, and same_sign;
  - the bound statement d <= T_m(n) + floor((Bbar-T) + t(r-k));
  - for INVALID or INCOMPLETE: word index, reason, the first bad letter or the z value, and
    the final vector prefix.
- **Mechanism reminder.** One line: each X that touches block j costs 2 on beta_j, and each
  net rotation step across block j costs 1.

Holdout families never appear in a packet.

## Engines and limits (when a campaign is approved)

The engines are GEPA, AdaEvolve and EvoX, plus a sequential control. They use the lift/sort
plumbing with all TRACE-AUDIT fixes. SkyDiscover settings:
- The evaluator returns an explicit `combined_score`. If it is missing, all numeric values
  are averaged.
- `cascade_evaluation` is false. The staged screen already handles it.
- `random_seed` is fixed.
- `inject_evaluator_context` is false.
- EvoX strategy evolution is **disabled**, because it writes and runs LLM-generated Python
  outside the sandbox, which AGENTS.md forbids.
- AdaEvolve uses `num_context_programs` <= 1 and has no sample-diff text.

Other limits:
- Output is capped at 8192 tokens.
- Preflight accepts the last fenced block that defines `certify`.
- Sub-caps are set per arm.
- GEPA uses `reflection_minibatch_size` 3 over families.
- The budget and model need explicit user approval before any live call. None is granted here.

## Cache and versions

The contract is `bound-contract-2` and the evaluator is `bound-eval-2` (bound-contract-1 and
bound-eval-1 before the 2026-09-25 bound-task hardening). The cache key is the
sha256 of: the source sha, the canonical family-list sha, the evaluator hash, the contract
and the sandbox flag. The evaluator hash covers `bound_*.py`, `lrx_m.py`, `lift_evaluator.py`
and `program_sandbox.py`. Runs with any INCOMPLETE family are never cached.

## What a certified m=11 set means

Each CERTIFIED m=11 family (a,S) gives this statement: for every l in Z_{>=1}^k and
n = 11 + sum l, d(V(a,S,l)) <= T_11(n) = 66 + 9(sum l - 1). This holds conditionally on
Lemma 1 as written by the group.

These parts are machine-checked:
- literal replay of every support word;
- the exact Profile coefficients;
- the exact rational criterion;
- literal lifted execution at the sampled z;
- an independent re-check by `bound_audit.py`, which uses the lrxm8 lineage with M = 11
  and shares no code with the evaluator.

These parts are not checked for all z: Lemma 1 itself, which was hand re-derived. This is
not a formal proof. It says nothing about the families that are not listed. At m = 11 there
are 11! (2^12 - 1) = 163,459,296,000 families, so no statement about E_r(n) at m = 11 follows.
