# Lift task: from certified m=8 families to m=9 (contract for evaluator, sets, proposers)

Date 2026-09-24. Goal: make GEPA, AdaEvolve and EvoX evolve a *gadget program*
that lifts certified m=8 family certificates to m=9. A gadget that works on
every frozen case and is uniform in m is the candidate for a label-insertion
lemma; the lemma plus the replicated m=8 base would give T_m(n) for all m>=8
by induction. Optimizers find the gadget; they do not prove it.

## Mathematics

- Conjecture: E_r(n) <= T_m(n) = m(m+1)/2 + (r-1)(m-2), n = m+r.
- m=8: T_8(n) = 6n-18 (proved by the group, replicated here).
- m=9: T_9(n) = 7n-25. Unit base with k blocks (r=k, n=9+k): T = 38+7k.
- Mixture criterion at m=9 (analog of the group's (7)): rational weights >= 0
  summing to 1, weighted base < 39+7k, every weighted stretch slope <= 7.
  Base and slopes are recomputed by the evaluator from literal words via the
  Lemma 1 lift macros; proposers never supply costs.
- T_{m+1}(n+1) - T_m(n) = n at fixed r. So an insertion gadget must add at
  most n letters and raise each slope by at most 1.

## Instance

An m=8 family is (a, S): a = label order (permutation of 1..8),
S = set of nonempty linear zero gaps, bits 0..8 (bit j = gap before label
j+1, bit 8 = trailing gap). Unit base = one zero per gap in S.

A lift instance inserts label 9 at label position i in {0..8} (0 = before
a_1, 8 = after a_8). Gap i of the parent splits into two gaps of the child.
If gap i is empty the child gap set is S shifted; if gap i is nonempty the
zeros go left, right, or both (both = split into two nonempty gaps). Each
instance is (parent family, i, split) and yields an m=9 family (a', S') with
its unit base. Instance id: `lift-<parent id>-i<i>-<left|right|both|none>`.

## Candidate

A Python program (executed only under the existing Seatbelt sandbox, as
authorized for the official-integration pilot) exposing
`lift(instance: dict) -> dict`.

Input `instance`:
```json
{"m": 8, "parent": {"id": "...", "labels": [..8..], "mask": 302,
  "unit_base": [4,0,1,0,7,0,8,5,0,6,3,2,0],
  "certificate": {"kind": "mixture|tree", "rows": [
     {"weight": "3/44", "word": "LXR...", "reference_labels": [...],
      "cut": 3, "base": 48, "slopes": [9,6,0,8]}]}},
 "insert": {"label": 9, "position": 4, "split": "both"},
 "child": {"labels": [...9...], "mask": 1234, "unit_base": [...], "k": 6,
           "budget_unit": 80, "slope_bound": 7}}
```
Parent certificate rows are literal words on the parent unit base after the
evaluator has already applied the group's transfer and projection, so the
program sees plain sorting words with exact base and slopes.

Output:
```json
{"words": ["LXLR...", "..."], "weights": ["1/2", "1/2"], "note": "..."}
```
`weights` optional; the evaluator also solves the exact LP over the given
words. Word length cap 4000 letters, at most 16 words per instance,
program wall limit 10 s per instance. Invalid output = failed attempt,
never repaired.

## Score (per candidate over the frozen development set)

1. `certificates`: instances where the exact mixture criterion holds (primary).
2. `gap_sum`: sum over failed instances of max(0, weighted base - (39+7k)) at
   the LP optimum plus slope excess; lower is better (search signal).
3. `valid`: instances with syntactically valid, sorting output.
4. Per-instance failure trace for reflection: which word failed to sort,
   base overshoot, which slope exceeded 7, parent rows used.
All secondary numbers are search signals, not mathematics.

## Sets

Development: 200 parent families (stratified by k=4..9 and by whether the
package certificate is direct, projected, or reverse-tree) x all insertion
positions x splits. Holdout: 100 disjoint parents, same construction, frozen
with hashes before any live call, evaluated once after finalist freeze.
Consumed m=8 confirmation sets are irrelevant here but are excluded anyway.

## Budget and controls

User-approved 2026-09-24: $150 total, Grok with reasoning capped at about
8k tokens via an enforced provider parameter, three engines. GEPA first;
AdaEvolve and EvoX start after GEPA shows one productive cycle (valid
proposal, selection, second proposal responding to feedback). Control:
fixed naive gadget (rotate to slot, bubble label 9 to place) and sequential
refinement with the same call budget. Report attempts, valid, invalid,
timeouts, dollars, mechanism traces, exact certificates.

## Schema decisions (lift evaluator, 2026-09-24)

Implemented in `integrations/lift_task.py` and `integrations/lift_evaluator.py`.

- Instance file: `{"schema": "lrx-lift-instances-v1", "set": "...", "instances": [...]}`.
  A bare list is also accepted. Each instance is the input dict above plus a
  top-level `"id"` (`lift-<parent id>-i<i>-<split>`) and `child.id`.
- Child family id: `m9-mask<mask>-labels<9 digits>`. Labels are joined with `.` when m+1 > 9.
- Child mask: parent bits j < i stay, bits j > i move to j+1. Split `left`
  sets child bit i, `right` sets bit i+1, `both` sets both. `none` is
  required exactly when parent gap i is empty. `k` = popcount of the child
  mask, `budget_unit` = T_9 = 38+7k, `slope_bound` = 7.
- The evaluator rebuilds `parent.unit_base` and all child fields from
  (labels, mask, position, split) and rejects any mismatch. Each parent row
  must be a literal word that sorts the parent unit base with no zero-zero
  swap. Its `base`/`slopes` are recomputed as the Lemma 1 direct profile and
  replace the stored values before the program sees them. Other row fields
  (`weight`, `reference_labels`, `cut`) pass through unchanged.
  `lift_task.comparison_word` turns a Lemma 3 comparison run into such a literal word.
- Output: every word must sort the child unit base with no zero-zero swap.
  Every word must also pass the literal stretched cross-check at z = 0, e_j,
  2e_j and three adjacent pairs. One bad word makes the whole instance
  INVALID_OUTPUT. `weights`, when present, must be a probability vector of
  rational strings, one per word. It is checked and reported, but the
  criterion uses the exact LP optimum.
- gap (contract `lift-contract-2`, evaluator `lift-eval-2`): for a valid miss,
  one exact LP gives min over mixtures of max(0, B-(39+7k)) + max(0, max_j slope_j - 7).
  Adding words never raises it. (The v1 rule, "minimize slope excess, then
  base", could rise when words were added.) Invalid output, a crash or a
  timeout adds 4000. combined_score = certificates + 0.5*valid/N + 0.5/(1+gap_sum/N).
- Staged evaluation (engines): the screen is 14 development parents, chosen by
  `lift_backends.screen_parents` and stratified by parent k. It is the
  selection score. A candidate that is valid on the whole screen and at least
  ties the best screen score so far also gets a full development evaluation.
  Finalists always get a full evaluation. A full evaluation of the naive seed
  takes about 57-81 s.
- Cache key: sha256 over the program source sha, the canonical instance-list
  sha, the evaluator hash (version plus the lift/sandbox source files), the
  contract string and the sandbox flag. Runs with any INCOMPLETE are never cached.
