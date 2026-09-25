# Best GEPA sort program (live-v2-gepa-260925-125146), read as a construction

Candidate `verified/evaluations/candidate-0131.py`, sha256 `4e6cfc22...`. The same bytes appear
as candidate-0136. Its recorded development result (`result-0131.json`, sort-contract-2):

- 1494/1500 states within budget, worst r = 5 at 295/300 (0.983);
- all 1500 sorted, 0 timeouts;
- mean excess 0.445, max excess 4, combined 1.6607.

The seed scored 1356/1500, worst r at 0.830, combined 1.4075.

Nothing was modified for this note. The candidate was re-run only in the Seatbelt evaluator,
on 300 development states, twice.

## 1. The algorithm

Notation follows the seed. The vector is a ring with a window pointer c; L and R move the
window and X swaps the two ring cells under it. A target is a pair (k, s): k is the ring
rotation at which label 1 must end, and s is the cyclic assignment of the r interchangeable
zeros to the zero slots. For a target, each entry gets an integer displacement rem on the
universal cover. It is the shortest way round, corrected so the displacements sum to zero.
Two adjacent entries must cross exactly when rem[x] - rem[x+1] >= 2. When both are zeros, the
cross is free: they exchange displacements with no letter. That is how zero blocks act as buffers.

**Phase A (ranked targets).** All n·r targets (k, s) are ranked by
est = (sum |rem|)/2 + min(k, n-k): a displacement mass plus the rotation distance of the
final window move. Targets are tried in that order.

**Phase B (window-routing policies).** For each target, 14 policies decide where the window
goes next. Each policy crosses one must-cross pair and repeats until every displacement is 0.
The window then moves the shorter way round to k. The policies are:

- continuous L or R sweeps (the seed's modes);
- nearest must-cross pair, preferring L or preferring R (the seed's greedy mode, in two variants);
- cost scores that weigh the displacement gap diff = rem[x] - rem[x+1] against the travel distance:
  2·diff - dist, and (diff-1)/(dist+1);
- lookahead scores that add a bonus when the cross creates a new must-cross pair next to the
  window, so the entry can be carried along;
- a score that also penalizes distance from the final window position k.

Each word is reduced freely: LR, RL and XX are deleted, L^n and R^n are deleted, and a run of
more than n/2 equal rotations is replaced by the shorter opposite run.

**Phase C (prefix escape, only if Phase B is over T).** A fixed list of about 45 short prefixes
is tried, such as XLXLXLXLL, RXRXRXRX or RXLXLXLLX. Most are "X then step" pumps that carry the
front pair one way. After each prefix, Phases A-B run again on the 12 best targets. When the
nonzero labels have at least C(m,2)·2/3 inversions (near-reversals), pump prefixes are tried
first.

**Stopping rule.** Phase B stops at 0.125 s and Phase C at 0.188 s of wall clock
(`time.perf_counter`). Otherwise it stops when a word within T is found and the next target's
est exceeds the current length (plus 6).

The only case analysis is: within T after Phase B, or not. There is also the near-reversal
threshold that reorders Phase C.

## 2. Difference from the cyclic-sweep seed

- **Same core.** The lift, must-cross rule, free zero-zero crossing, target set (k, s) and
  final rotation are the seed's.
- **Ranking.** The seed tries every target in index order and keeps the shortest word. The
  candidate ranks targets by the est lower-bound proxy and stops early.
- **Policies.** The seed has 3 sweep modes; the candidate has 14. The new ones are
  cost-weighted and lookahead greedy choices of the next crossing, all heuristic.
- **Stronger reduction.** Rotation runs longer than n/2 are rewritten the shorter way round.
- **Prefix escape.** Phase C is new. It is a bounded search over hand-listed prefixes, targeted
  at near-reversals, where the seed was over T.
- **Wall-clock deadlines.** They are new, and they make the output machine- and load-dependent.
  In two identical Seatbelt re-runs on 300 development states, one state's length changed from
  69 to 71 (m9r5-566485793). The first re-run matched the recorded lengths exactly.

Conceptually, it is the seed plus a portfolio: about 14 policies × n·r targets × up to 45
prefixes, followed by a take-the-minimum. It adds no new routing idea that would carry a
length argument.

## 3. The 6 development states it still misses (length reproduced in both re-runs)

| id | v | r | d | T | length | seed length | why |
|---|---|---|---|---|---|---|---|
| m9r2-1995839 | (2,1,0,0,9,8,7,6,5,4,3) | 2 | 52 | 52 | 53 | 53 | Reflected root at d = T. It needs an exact geodesic, and the best portfolio word is 1 over d. |
| m9r5-163688734 | (3,4,2,1,0,0,0,0,9,8,7,6,0,5) | 5 | 72 | 73 | 74 | 78 | Near-reversal with the zero block split 4+1 around 6 and 5. It needs excess <= 1 and gets 2. |
| m9r5-164021038 | (4,3,2,1,0,0,0,0,9,8,6,7,0,5) | 5 | 72 | 73 | 74 | 74 | Same split-block near-reversal, with 6 and 7 swapped. Excess 2 against slack 1. |
| m9r5-164021332 | (4,3,2,1,0,0,0,0,9,7,8,6,0,5) | 5 | 72 | 73 | 74 | 78 | Same family. Excess 2 against slack 1. |
| m9r5-220240558 | (5,4,3,2,1,0,0,0,0,9,8,7,6,0) | 5 | 72 | 73 | 74 | 76 | Reversal with the zeros split 4+1. Excess 2 against slack 1. |
| m9r5-164021374 | (4,3,2,1,0,0,0,0,9,8,7,6,0,5) | 5 | 73 | 73 | 75 | 79 | Extremal state (d = T). It needs a geodesic and gets excess 2. |

All six are near-reversals with d >= T-1. Five of them have a lone zero separating the last one
or two labels from the zero block. On these states any excess above T - d (0 or 1) fails, and
the sweep family reaches excess 1-2 at best. No policy in the portfolio sends the lone zero to
its block without an extra pass.

## 4. Length as a function of the state

Maximum produced length per r on development:

| r | T | max length | max length - d | max length - inv |
|---|---|---|---|---|
| 1 | 45 | 45 | 4 | 27 |
| 2 | 52 | 53 | 4 | 35 |
| 3 | 59 | 59 | 4 | 45 |
| 4 | 66 | 66 | 4 | 53 |
| 5 | 73 | 75 | 4 | 62 |

Here inv is the number of inversions among the nonzero labels read linearly, at most 36.

There is no obvious bound in terms of n, r and inversions. The length is a minimum over a
wall-clock-truncated portfolio, not one route. Its gap to the label inversion count grows about
7-9 per unit of r and depends on where the zeros sit, not just how many there are. The lifted
displacement mass used for ranking, (sum |rem|)/2 + rotation, is off from the length by 0 to
54. The only tight regularity on this sample is `length <= d(v) + 4`, with max excess 4 at
every r. That is stated in terms of d, not n, r or inversions, so it gives no route to T.

The observed maximum is T at r = 1, 3, 4 and exceeds T at r = 2 (+1) and r = 5 (+2). So even
`length <= T` is false for this program on development, and no conjecture of the form
length <= T is supported. A conjecture worth recording is that the one-route seed core (a
single policy, no portfolio) might satisfy length <= T + c(r) with small c. It would need its
own evidence, because the seed exceeds T by up to 6 at r = 5 (79 vs 73).

## 5. Uniformity in m

The code contains no literal 9. The only 9s are in the sentinel values 10**9. It reads
m = max(v), r = n - m and T = m(m+1)/2 + (r-1)(m-2), and every loop runs over n, r or the
target set. So it is syntactically uniform in m and r, and it runs for general m.

It is not uniform in two other senses:

- The prefix list and the near-reversal threshold (C(m,2)·2/3) are hand-tuned constants
  aimed at the m=9 failures.
- The wall-clock deadlines make its output depend on hardware, load and m. Larger m explores
  fewer targets and policies within 0.125 s.

Holdout (9,6) and (10,3) will show how it degrades. It has not been evaluated there, because
the holdout is reserved for the post-freeze finalist check.
