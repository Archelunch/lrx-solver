# Constructive routing lemmas toward zero insertion

The main LRX sorting-radius conjecture remains open. The following are
auxiliary, conditional lemmas with explicit proofs, not a proof-assistant
formalization or a claim of novelty in the literature. Let m>=2, r>=1,
n=m+r. Terminal marks are all positions j>=m.

## 1. Fixed-projection normal form and exact routing

Fix a smaller sorting word V of length ell from u, with every letter changing
the smaller visible vector. In particular, V contains no X applied to two
plain zeros. Consider full words whose uncancelled projection letter sequence
is exactly V, not merely the same permutation.

Every such full word has the form

    Z_0 V_1 Z_1 V_2 ... V_ell Z_ell,

where each Z_i preserves the smaller vector. Ignoring identity self-loops,
these zero-projection moves are exactly

    1 --X--> 0 --L--> n-1,
    1 <--X-- 0 <--R-- n-1.

All other marked positions have only identity closure. X on two plain zeros
is another identity self-loop; it cannot improve a shortest repair.
The underlying unlabelled graph is the bidirectional path 1--0--(n-1),
with the displayed generator labels depending on direction.

**Proof of normal form.** Split a full word at precisely its projection-changing
moves. Each intervening block traverses this zero-projection graph, since the
smaller vector is constant throughout it. Replace a block by a shortest path
with the same endpoints. The smaller vector and terminal marked position of
the block are unchanged, so all later moves remain valid. A shortest path
has length at most two. Thus a shortest feasible fixed-word lift exists in
this form with each repair block of length <=2. Conversely any concatenation
of such valid blocks and the prescribed projected letters is a lift. QED.

For a prescribed projected letter, allowed marked transitions are

    L: j>0     -> j-1
    R: j<n-1   -> j+1
    X: j>=2    -> j.

Initialize final costs using shortest zero-projection paths to ANY j>=m.
Working backward through V, minimize repair length + 1 + suffix cost over
at most three closure endpoints for each mark. This enumerates every normal
form, so it returns the exact fixed-word minimum or proves no lift of that
particular word exists. Time and storage are O(n(ell+1)); reconstructing one
witness is linear in its output length. Checking V itself costs O(n ell).

A feasible normal form has length <=3ell+2. This loose bound explains the
implementation's finite infinity sentinel; it is not the conjectured bound.
Fixed-word infeasibility is never reported as infinite H_q or as a negative
answer for A_q. Other smaller sorting words can behave differently.

Implementation: `integrations/word_lift.py`. Positive outputs are replayed by
the unchanged trusted CertificateValidator, including exact projection letters.

## 2. A constructive amortized left-sweep bound

Suppose V uses only L and X, sorts u, and every letter changes u. Let k be
its number of L letters and j_0 the initial marked position. Perform this
explicit construction:

- Before projected L at mark 0, insert L, sending the mark to n-1; then
  perform the projected L as usual.
- Before projected X at mark 0, insert L, sending the mark to n-1.
- Before projected X at mark 1, insert XL, sending 1 to 0 to n-1.
- All other projected letters need no repair.
- At the end, if the mark is 0 append L; if it is 1 append XL.

All inserted moves preserve the smaller vector. If the final mark lies in
positions 2,...,m-1, this particular construction misses the terminal set;
no global infeasibility is inferred. Otherwise it is a sorting lift and its
routing overhead satisfies

    overhead <= 2 floor((k+n-1-j_0)/(n-2)).                 (1)

**Proof.** Regard each inserted L or XL block as one repair. Every repair
increases the numeric marked position by n-1 (from 0) or n-2 (from 1), and
costs at most two full moves. Each projected L decreases it by one; projected
X leaves it unchanged. If there are h repairs, including any final repair,
and the resulting mark is j_f, then

    sum(repair increments) = j_f-j_0+k <= n-1-j_0+k.

Each increment is at least n-2, hence
`h <= floor((k+n-1-j_0)/(n-2))`. Cost <=2h proves (1). The prescribed moves
project exactly to V; if the endpoint is allowed, the smaller root together
with that mark is the full canonical root. QED.

This is a structural sufficient condition, checkable from V and j_0 before
searching full states. It does not assume a short full sorting word exists.
For Q=T(m,r-1), it supplies the desired lifting certificate whenever the
endpoint condition holds, |V|<=Q+1, and

    |V| + 2 floor((k+n-1-j_0)/(n-2)) <= Q+m-2.

For example, for every m>=2,r>=1 take j_0=n-1 and V=L^(n-2)X. Let u be the
inverse image of the smaller root under V. All letters change u. The mark
reaches 1 before X, so XL repairs it; overhead is exactly 2 and (1) is sharp.
This is an infinite family, not evidence that arbitrary vectors admit V
of the required type and length. For the conjecture domain m>=8,r>=2 its
full length n+1 is below T(m,r).

**Coverage limit.** None of the geodesic words produced for our hard (8,5)
and (8,9) test families uses only L/X. Their successful certificates use the
more general fixed-word router. Extending this amortized argument to mixed
left/right sweeps is still necessary before it can explain those witnesses.

## 3. A free-trajectory subclass (from the audited Grok proposal)

For any projected sorting word V, assign displacements -1 to L, +1 to R,
and 0 to X. Starting from j, form the unwrapped positions p_i after its
prefixes. If each letter is legal at its preceding p_i (L needs p_i>0,
R needs p_i<n-1, X needs p_i>=2), and the final position belongs to
{0,1} union {m,...,n-1}, then V itself followed by at most two repair moves
sorts the full vector. Append nothing, L, or XL according to its endpoint.
The proof is direct induction on the letters followed by zero-projection
closure. In particular, for m>=8 and |V|<=Q+1, full length <=Q+3<=Q+m-2.
Again the missing theorem is existence of such a word and marking for every
vector, not correctness of the stated conditional construction.

## Connection to the final goal

A constructive proof still needs to show that every full vector admits a
suitable deletion and a suitable smaller word, assuming the smaller bound.
The induction hypothesis guarantees some short smaller word; it does not
provide these routing properties. The general r=2 base is also unresolved.
The finite certificates in this iteration cannot fill either universal gap.
