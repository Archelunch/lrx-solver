# Zero-erasure identity and bounded-search lemma

The LRX sorting-radius conjecture remains open. These are elementary auxiliary
lemmas with explicit arguments, not a proof of the conjecture, a literature
novelty claim, or a proof-assistant formalization.

## 1. Exact counting identity

Let m >= 2, r >= 1. Start from any visible vector containing the distinct
positive tokens 1,...,m and r zeros. Give the zeros temporary distinct labels
and transport those labels through every move of an arbitrary word W,
including swaps of two zeros. Write ell = |W|.

For each initially labelled zero z, delete its current position after each
move. Let p_z(W) count the transitions on which this smaller visible vector
changes, without cancelling subsequent inverse transitions. Define:

- S(W): number of X moves whose two swapped tokens are both zeros.
- I_z(W): number of L moves carrying z from the first to last position,
  plus R moves carrying z from last to first, plus X moves swapping z with
  a positive token.

Then, for every labelled zero,

    p_z(W) = ell - S(W) - I_z(W).

**Proof.** For L or R, deleting the boundary-crossing zero makes the smaller
vector unchanged; deleting any other zero leaves one smaller rotation.
That rotation changes the vector: a vector with at least two distinct
positive tokens cannot be fixed by a one-position cyclic rotation.
For X swapping two positive tokens, every deletion leaves a nontrivial
smaller X. For X swapping a positive token with a zero, precisely deletion
of that swapped zero makes the smaller vector unchanged. For X swapping
two zeros, every deletion makes the smaller vector unchanged: if the
marked zero participates, the two possible deletions of that adjacent
zero pair coincide; otherwise the smaller swap is between equal zeros.
These cases are exhaustive. The invisible moves for z partition into the
S moves and its I_z moves, which are disjoint. Subtract their count from
ell. This also explains why zero labels must be transported through 00
swaps even though the visible vector does not change. QED.

In particular, writing Z = sum_z I_z,

    min_z p_z = ell - S - max_z I_z
              <= ell - S - ceil(Z/r).

Also sum_z p_z = r(ell-S)-Z. The helper
`integrations/zero_erasure.py` computes every p_z in O(m+r+ell) time and
O(m+r) space. This is a search-side convenience; certificates still go
through the unchanged trusted replay checker.

## 2. Fixed-word lifting certificate

If W sorts the visible vector v, every labelled zero ends in the final
zero block. Hence for any q and B, a sorting word with ell <= B and

    S + max_z I_z >= ell-q

supplies a witness to A_q(v) <= B. Equivalently, that particular word has
an admissible deletion exactly when the displayed inequality holds.
The average-count sufficient condition is S+ceil(Z/r) >= ell-q.
This follows directly from Lemma 1 and the definition of H_q; it does not
construct W and is not a universal existence theorem.

For the proposed conjecture-facing step, let
Q = T_m(m+r-1), B = Q+m-2, q = Q+1. A sorting word of length B needs
S+max I_z >= m-3. Shorter words need only ell-Q-1 erasures (automatically
satisfied when that number is nonpositive). Establishing suitable words
for all v is the unresolved mathematical work. The general base case
must also be proved. Finite tests cannot supply either universal argument.

## 3. Admissible remaining-length bound

In a partial lifted path of full length t, let w be the current smaller
visible vector and d(w) its exact distance to the smaller root. Any full
continuation of length k induces a smaller path with at most k moves:
each full move projects to either one smaller move or no change. If the
continuation sorts, k >= d(w). Thus no completion within full bound B
exists when t+d(w)>B.

This proves the safety of pruning such states in `forward_h`. The
projection-budget constraints and existing slack dominance are unchanged.
If pruning exhausts the frontier, only H_q>B is certified. The result is
COMPLETE_BOUND, never an assertion of infinite H_q. Resource exhaustion
remains INCOMPLETE. Unbounded searches do not use this pruning rule.

## Verification and limitations

The counting implementation is compared with trusted labelled replay for
every word of lengths 0 through 4 and every visible vector in graphs
(2,1), (2,2), (2,3), (3,1), (3,2). These tests check the implementation;
the general statement rests on the move-case proof above.

The bounded search is compared with the independent exhaustive lifting DP
on every visible vector of (3,3), at three projection caps and bounds on
both sides of the exact answer. A separate regression checks that early
pruned exhaustion is bounded, although an unbounded finite lift exists.
See the session report for actual test outcomes and targeted finite scope.

## A concrete limit of average-only feedback

The length-60 witness in `tight-witness.json` starts at
`(0,0,0,0,8,7,6,5,0,4,2,1,3)`. It has S=0 and individual erasure counts
`(4,4,4,2,6)` for initial zero positions `(0,1,2,3,8)`. Every projection was
independently replayed. The exact best projection is 60-6=54, whereas the
average-only upper bound is 60-ceil(20/5)=56. Thus average-only feedback
would fail to certify this word at q=55 even though one deletion certifies
q=54. Any proposed erasure-based construction should retain the per-zero
profile and account for concentrating enough erasures on one zero.
This concerns this word; it does not exclude other suitable words for the
other initial markings, and 'tight' here means reaching our allowed length,
not a proved optimal sorting distance.
