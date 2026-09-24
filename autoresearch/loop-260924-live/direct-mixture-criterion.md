# Conditional direct-word mixture criterion

This is a reusable construction rule, not an unconditional sorting-radius
result. It is the proof obligation implemented by `program_evaluator.py` for
each named m=8 family. It works algebraically for any m when the same word
expansion is valid; the current evaluator validates only m=8 and 4–7 blocks.

Fix one permutation of labels 1..m and k selected zero gaps. Replace each
selected gap by one zero to get the **unit-block state**. For each complete
LRX word `w` that sorts this state, delete swaps between two visible zeros and
cancel adjacent inverse rotations. Track the k zero blocks individually in
the resulting word. Let `s_j` be the number of swaps between block j and a
nonzero label. Partition rotations into gaps before, between, and after swaps.
In gap t, let `g_{t,0}` be the signed number of original unit rotations, and
start `g_{t,j}` at the signed number of those rotations carrying block j. Add
**+1** to `g_{t,j}` when the gap ends in a swap with block j on the left; add
**-1** when the gap begins just after a swap with block j on the right. These
boundary adjustments account for the rotation prefix or suffix of the
zero-block swap macro. Set

    B(w) = #X + sum_t |g_{t,0}|,
    beta_j(w) = 2 s_j + sum_t |g_{t,j}|.

For positive block lengths `ell_j`, lift each atomic rotation across block j
to `ell_j` rotations. A swap with block j on the left uses
`L^(ell_j-1) X (RX)^(ell_j-1)`; a swap with it on the right uses
`X (LX)^(ell_j-1) R^(ell_j-1)`. Each full macro has length `3 ell_j-2`.
Its internal X and repeated RX or LX contribute `1+2(ell_j-1)`; the
remaining `ell_j-1` boundary rotations join the preceding gap (left block,
+1) or following gap (right block, -1). The lifted word sorts the expanded
visible state. After canceling inverse rotations, its length is at most

    #X + sum_j 2 s_j (ell_j-1)
       + sum_t |g_{t,0} + sum_j g_{t,j}(ell_j-1)|,

and hence at most

    B(w) + sum_j beta_j(w) (ell_j - 1).                    (1)

The last step is the triangle inequality in each gap. Inverse rotations
produced by expansion can only shorten the literal word. `resources()`
computes exactly these boundary-adjusted g values, B, and beta from the
normalized unit word; the parent replays that word and audits literal lifts.

Now take nonnegative rational weights on finitely many such words summing to
one. If their weighted B is **strictly below** `T_m(m+k)+1` and every weighted
beta_j is at most `m-2`, then for every positive length vector the weighted
mean of the upper bounds (1) is strictly below

    T_m(m+k)+1 + (m-2) sum_j (ell_j-1)
      = T_m(m+sum_j ell_j)+1.

At least one component word therefore has integer length at most
`T_m(m+sum_j ell_j)`. Thus the whole named family obeys the target bound for
arbitrary positive lengths. For m=8, the base threshold is `31+6k` and the
slope cap is 6. This criterion concerns one fixed label order and gap mask;
neither a finite set of such certificates nor failure to find one proves the
general LRX conjecture.
