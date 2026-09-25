# SPEC, Track 2: map and design for the bounded-construction task

Date 2026-09-25. This is a design document. No repository code was modified. The contract is
`TASK.md`, in the same directory. Results cited here are either earlier repository evidence
(with its path) or scratch calibration probes run for this spec (see section 4). The probes
used trusted repository code only and ran no generated code.

## 1. Why this task

The earlier campaigns fell short in these ways:
- lift: every arm finished at 190/2295 on the holdout, tied with the sequential control.
- corr: 0/8 on the holdout.
- sort-m9: engines won, but by assembling a portfolio of heuristics, with no length bound.

The REPORT-FOR-AGENTS summary says no engine has ever produced a construction with a length
bound. The sort-m9 REPORT recommends rewarding "bounded constructions" next.

Track 2 makes the score itself a bound. A candidate returns words for a whole family (a,S).
The evaluator prices the words with the group's Lemma 1 macros, which are exact and affine
in the block lengths. An exact LP then either certifies d(v) <= T_m(n) for every state of the
family, at every r, or reports the smallest additive and per-zero excess that the words prove.

Three properties follow:
- **No BFS tables.** Scoring is exact at any m, so m = 11 (and 12 or more as a stress test)
  is as cheap as m = 9. This is the first holdout on an m where no distance table exists.
- **Search exploits do not pay.** Per-state search is useless because the certificate has to
  hold for infinitely many states at once. Per-family word search within 3 s CPU is allowed;
  if it certifies, the certificate is still a real theorem for that family.
- **The packet is actionable.** A failure names the zero block j whose slope exceeds m-2 and
  says which X crossings or rotation passes cause it. GEPA reports 4-6x faster convergence
  with actionable side information, and Meta-Harness found full traces better than bare
  scores.

## 2. Map: existing pieces and reuse

| need | existing code or data | reuse |
|---|---|---|
| executor, Lemma 1 profile, literal lift check, (7) | `integrations/lrx_m.py` (`Profile`, `z_samples`, `literal_lift_check`, `mixture_criterion`, `budget`, `base_vector`) | as is; m is inferred from the state |
| exact LP, gap LP | `integrations/lift_evaluator.py` (`simplex`, `mixture_lp`, `gap_lp`, `_parse_output`) | import; `MAX_WORDS` becomes 32 in the bound evaluator's own parser |
| sandboxed candidate run | `lift_evaluator.run_program`, `program_sandbox`, `program_evaluator._preexec` | copy the pattern with `bound_worker.py` calling `certify`; batch CPU limits from `sort_worker.py` |
| family ids | `lift_task.family_id` | as is (labels joined with `.` when m > 9) |
| independent audit | `lift_audit.checker(m)` loads `verify-m8-260924/checker/lrxm8.py` with M = m | new `bound_audit.py` on the same loader, without parent/child logic |
| controls | `sort_control_naive.py`, `sort_control_sweep.py` (`_lifts`, `_sweep`, `_reduce`) | wrap in `bound_control_*.py`; no edits to the originals |
| tight families (m = 9) | `outer-layer-260925/class_m9_r{1..5}_full.json` `argmax_cls` | read by the builder |
| (10,3) states at T | `sort-m9-260925/frozen/holdout.json` | read if present |
| positive controls | `lift-m9-260924/finalists/audit.json` (84 audited m = 9 child certificates), `lift-m9-260924/frozen` parents (m = 8 literal rows) | tests: the bound evaluator must certify them |
| engine plumbing | `sort_backends.py`, `lift_backends.py` (sub-caps, rejection notes, minibatch, first-prompt guards) | new `bound_backends.py` (search-side), mirroring `sort_backends` |

TRUSTED lock: nothing listed in `tools/orchestrator.py` TRUSTED changes, and
`python tools/orchestrator.py trusted` printed `{"ok": true, "changed": [], "missing_from_lock": []}`
on 2026-09-25. The new `integrations/bound_*.py` evaluator files decide truth, so they must go
into the campaign approval hash. A human may add them to TRUSTED and re-lock; agents do not.

## 3. Mathematics, precisely

### 3.1 Families and budget

A state with labels 1..m and r >= 1 zeros decomposes uniquely in the linear frame as (a,S,l):
- a is the label order;
- S is the set of nonempty gaps, where gap g is the one after g labels;
- l_j >= 1 are the block lengths.

The union over all (a,S) is the whole state space for every r. The m = 8 checker enumerated
exactly this partition (`checker-report.md`, limitation 5).

T_m(n) - T_m(n-1) = m - 2 when r grows by 1 at fixed m. So with z = l - 1,
T_m(m + k + sum z) = T_m(m+k) + (m-2) sum z. This identity is the only place m enters the
criterion.

### 3.2 Lemma 1 (group's), as implemented

The rules are the table in TASK.md, from `lrx_m.Profile` (lines 157-262). The profile does
three things:
1. It counts per segment: d is the unit rotation, and cz_j is the number of times the cursor
   crosses block j (with sign).
2. It counts X letters (q), and for each block j the number of Xs that involve it (A_j).
3. It closes a segment at every X. For a (zero, label) swap it moves the L^{z_j} prefix into
   the current segment. For a (label, zero) swap it moves the R^{z_j} suffix into the next
   segment.

The cost F(z) is piecewise linear and convex along rays, and F(z) <= B + beta.z. Nothing in
the macros depends on m.

### 3.3 Criterion (7), generalized to m, and its proof

Take any mixture w with Bbar < T_m(m+k) + 1 and betabar <= m-2. For each z >= 0,
min_i F_i(z) <= sum_i w_i F_i(z) <= Bbar + betabar.z < T_m(n) + 1. Since d(V) <= min_i F_i(z)
and d(V) is an integer, d(V) <= T_m(n).

This is the group's (7) with 6 replaced by m-2 and 30+6k by T_m(m+k). `lrx_m.mixture_criterion(m=...)`
and `lift_audit` already use this form. The generalization is the same one-line argument; the
group should still confirm it, since the manuscript states it for m = 8.

### 3.4 The gap and why "certified iff gap == 0" is wrong

`gap_lp` minimizes u + t subject to Bbar - u <= T+1 and betabar_j - t <= s. So g = 0 when
Bbar = T+1 is reachable with slopes within bound, even if nothing lower is. The scratch probes
hit this 3 times:
- m = 9, k = 3, random order;
- m = 11, k = 4, reversal;
- m = 11, k = 1, refl.

In each case g = 0 but `mixture_lp` gave min Bbar = T+1. The contract therefore reports a
third status, BOUNDARY, and counts certificates by the status. It keeps g as the monotone
search signal (it never grows when words are added, per lift-contract-2).

### 3.5 Bound statement

From any mixture w, with t = max(0, max_j betabar_j - s), every state of the family satisfies
d(v) <= floor(Bbar + (s+t) sum z) = T_m(n) + floor((Bbar - T) + t (r - k)). This is the
"proof-shaped" reading of a miss: an additive excess plus a per-extra-zero excess. The packet
prints it, and the worst g over a set is the bound for that set. It is a theorem only when
every family is valid.

### 3.6 Edge cases

- **k = 1.** T = m(m+1)/2, and the certificate also covers r = 1. The root family (identity,
  {m}) is certified by the empty word (B = 0, beta = 0), which is a unit test. The k = 1 tight
  families of section 5 are in the unscored edge set. At m = 8, 338 of 362,880 one-block bases
  needed mixtures, and all passed (7) (`checker-report.md`).
- **Leading and trailing gap.** Bits 0 and m are separate linear atoms even though they are
  cyclically adjacent. An X across the wrap between them is a zero-zero swap and INVALID.
  Rotating across the wrap is fine.
- **Empty gaps.** Gaps outside S hold no zeros. The family never covers states with zeros
  there; those belong to other families. S = 0 (r = 0) is out of scope and rejected.
- **k = m+1.** Only one mask exists (all bits set), so the stratum varies only the order.
- **Non-same-sign segments.** B + beta.z is still an upper bound, which is sound. The packet
  reports `same_sign` because a different segmentation could lower the price.
- **Literal lift mismatch.** Lemma 1 says this cannot happen, so a mismatch is an evaluator
  or lemma alarm. The family becomes INVALID_OUTPUT with the flag `lemma1_literal_failure`,
  and a human must review it before any claim.
- **Timeouts and crashes.** These are INCOMPLETE and get g = 4000. They are never "no
  certificate", and runs that contain them are never cached (AGENTS.md).

### 3.7 Known ceiling: (7) alone may not suffice

At m = 8 the group needed leaf trees (8) for 37,323 two-zero and 639,357 three-zero bases, and
reverse-tree transfers for some k >= 4 families. Some families may therefore be
(7)-infeasible for every word set, in particular the tight ones. The certified fraction has a
ceiling below 100% that we do not know.

A contract-2 extension is specified here and not built. It would let a candidate return a
split tree over boxes of z, each leaf a mixture, scored by `lrx_m.leaf_criterion` and
`tree_leaves` with T_m. That also changes the gap definition (max over leaves of the leaf
excess), so it waits until contract-1 results show that low-k failures dominate.

## 4. Calibration (scratch probes, not frozen sets)

The probe scripts are in the session scratchpad. They are `probe_bound.py` (seed 260925),
`probe_mix.py` (seed 7) and `probe_hard.py` (seed 11). They imported `lrx_m`, `lift_evaluator`
and `sort_control_*` and modified nothing.

**Single words** (probe 1, 4 families per k):
- The naive bubble word has base -11 to +192 relative to T and max slope -1 to +37 relative to s. Its gap is 8-224.
- The best single sweep word has base 9-43 **below** T, but max slope -5..+9 over s.
- **The binding constraint is slope, not length.** Sweep sorting crosses zero blocks too often.

**Mixtures of sweep variants on random orders** (probe 2, 3 families per k, k = 2..m+1):

| m | families | top-16 by max slope + LP: certified | full pool LP (b): certified | worst gap (b) | wall s (b) |
|---|---|---|---|---|---|
| 9 | 27 | 14 | 22 | 1/2 | 14.6 |
| 10 | 30 | 21 | 29 | 17/96 | 19.8 |
| 11 | 33 | 22 | 31 | 46/59 | 32.1 |

**Structured orders, full pool LP (b)** (probe 3, 2 masks per k, k = 1..m+1, certified/total):

| m | reversal | rev_rot | near_rev | refl | identity | id_rot | wall s |
|---|---|---|---|---|---|---|---|
| 9 | 4/20 (worst g 21/8) | 9/20 | 4/20 | 7/20 | 20/20 | 20/20 | 44 |
| 10 | 6/22 (305/62) | 4/22 | 7/22 | 7/22 | 22/22 | 22/22 | 74 |
| 11 | 5/24 (4) | 12/24 | 8/24 | 7/24 | 24/24 | 24/24 | 111 |

These probes lead to four design decisions:
1. **Frozen sets are weighted toward reversal-type orders.** Uniform random families would be
   about 80-95% certified by control (b) alone, and the score would saturate. TASK.md gives
   about 10 of 17 slots per stratum to rev_rot, near_rev and refl, and 1 to easy orders as a
   saturation check.
2. **Control (b) is strong and cheap.** It averaged about 0.8 s per family in pure Python and
   already yields genuine m = 11 family certificates, with no model involved. Any engine claim
   must beat (b) on the holdout. The seed is (b16), not (b), so selection-only gains are
   visible and separable from new constructions (the lift lesson in `TRACE-AUDIT` section 2).
3. **CPU limit.** 3 s per family lets a candidate run an exact LP over a few hundred words, so
   a (b)-class construction is reachable. A full development evaluation is at most about 15
   CPU-minutes worst case, or about 4 min with 4 jobs. The 30-family screen is at most 90 s.
4. **Word cap.** 32 words, because the probe support needs up to k+1 <= 13 words.

These numbers come from small unfrozen samples. They set expectations and are not results.

## 5. Sets, precisely

The builder is `autoresearch/bound-m-260925/build_frozen.py` (stdlib). For each (set, m, k)
stratum it does the following:

1. Draw masks without replacement from the k-subsets of {0..m} with `random.Random(seed)`.
   Force one mask with bits 0 and m both set and one with neither, when k >= 2 and such masks
   exist.
2. Assign order classes in the fixed counts from TASK.md:
   - rev_rot: a uniform rotation s in 0..m-1, with s = 0 at least once per m-set;
   - near_rev: a uniform adjacent transposition, then a uniform rotation;
   - refl: a uniform rotation of (2,1,m,...,3);
   - high_inv and easy: rejection sampling with at most 10^4 tries, and a loud failure if the
     tries run out;
   - uniform: `rng.shuffle`.
3. Reject duplicates and any (a,S) already in an earlier set. The order is development,
   holdout, then edge.
4. For m = 9 development, replace high_inv or uniform slots in k = 2 and k = 3 with the
   7 tight families listed in TASK.md, derived from `argmax_cls`. Assert that each derived
   (a,S,l) rebuilds the stored vector.
5. Write `{"schema": "lrx-bound-families-v1", "set": ..., "families": [...]}`. Each family
   holds id, m, labels, mask, gaps, k, unit_base, budget_unit, slope_bound, class, inv and
   tight_source. Also write `manifest.json` with the seeds, counts per (m, k, class) and
   sha256 values.

## 6. Evaluator behavior (`integrations/bound_evaluator.py`, planned)

For each family:
1. Recompute every field from (labels, mask) and reject any mismatch.
2. Run the candidate (sandbox) or a trusted control (`--no-os-sandbox`, refused for generated
   sources).
3. Parse the output (at most 32 words).
4. Check each word with `Profile`, then with `literal_lift_check` at `z_samples(k, pairs=k-1)`
   plus the all-ones vector.
5. Solve `mixture_lp`, then assert that `mixture_criterion(m=m)` agrees (a disagreement is an
   evaluator bug, raised, never scored).
6. For a family that is not certified, solve `gap_lp`.
7. Set the status and the bound statement, and build the packet data.

The aggregates and `combined` follow TASK.md. The CLI refuses to overwrite an output file.
The holdout goes through a separate `--holdout` flag that needs a frozen-finalist manifest,
as in `sort_evaluator`.

## 7. Build plan (not started; each item small)

1. `integrations/bound_task.py`: family construction, validation and ids (about 80 lines).
2. `integrations/bound_worker.py`: `certify` bridge with per-family ITIMER_PROF/REAL, like
   `sort_worker` (about 60 lines).
3. `integrations/bound_evaluator.py`: sections 3 and 6 (about 250 lines, reusing the LP).
4. `integrations/bound_audit.py`: a lrxm8 loader with M = m; it re-derives each unit base,
   replays and lifts the words, and checks the claimed witness exactly (about 90 lines).
5. `integrations/bound_control_naive.py`, `bound_control_sweep.py` (b16, b and b'), and
   `bound_control_sortprog.py` (c, sandboxed).
6. `autoresearch/bound-m-260925/build_frozen.py` plus the frozen sets and manifest, then
   controls on development, then control (b) on the holdout. The holdout controls are trusted
   code, so running them does not consume the one-shot holdout.
7. `integrations/bound_backends.py`, search-side, mirroring `sort_backends` with all TRACE-AUDIT
   fixes and SkyDiscover settings. This includes the first-prompt guards, with the seeded
   SkyDiscover RNG (GUARD-NOTE fix), captured twice.
8. Tests in `tests/test_search_bound_*.py`:
   - family and mask construction for m = 9, 10, 11 and k = 1..m+1;
   - the root family certified by the empty word;
   - a wrap X between the gap-0 and gap-m blocks rejected;
   - BOUNDARY detection on a synthetic cost set (Bbar = T+1);
   - g monotone under added words;
   - float weights rejected and weights never trusted;
   - a corrupted word rejected and a wrong-family word rejected;
   - the preflight table guard;
   - positive controls: the 84 audited m = 9 lift certificates are CERTIFIED, and
     direct-mixture m = 8 lift parents are CERTIFIED at m = 8;
   - the audit agrees with the evaluator on the development controls, with 0 disagreements.
9. Verify with the three commands in AGENTS.md plus `python tools/orchestrator.py trusted`.

## 8. Risks and open questions

- **(7)-only ceiling.** Section 3.7. If the tight or low-k strata stay uncertifiable for every
  arm, including (b), the result is informative, but it points to the contract-2 trees, not
  more search.
- **The control may dominate.** (b) is a deterministic LP over a fixed pool, and engines may
  only rediscover it. Starting from (b16) and requiring a holdout win over (b) keeps any claim
  honest. A win on rev_rot and near_rev at m = 11 would be the first engine result that is
  also a theorem.
- **The generalization needs the group's review.** Section 3.3 states (7) for general m. The
  argument is one line, but the manuscript is stated for m = 8 only.
- **Uniformity is only screened.** The AST guard catches tables, not `if m == 9:` branches.
  m = 11 is the real test. Finalize should also report per-m results and grep the finalists
  for m-literals.
- **Determinism.** The sort-m9 GEPA finalist is slightly nondeterministic. Finalize runs each
  finalist twice on the screen and reports whether the outputs are identical. A
  nondeterministic certificate is still valid because the words are what is checked.
- **Budget.** No live call is authorized. The task is designed so the controls and all offline
  work (steps 1-6 and 8) need no provider. The user asked to keep usage within their limits,
  so any campaign proposal should state per-arm call caps and use the cheapest model that
  passes a 1-call probe.
