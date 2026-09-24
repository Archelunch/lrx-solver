# Two exact LRX family certificates

24 September 2026. This note gives two upper-bound certificates for **named families** of LRX states. All displayed fractions are exact. “New” below means that a certificate uses a direct word outside the specified frozen finite pool; it makes no claim of priority in the literature. The expansion and rational-mixture framework comes from the user-supplied nine-gap `m=8` manuscript attributed to Chaos_ghost. The direct certificates here adapt that existing method. Human mathematical peer review and Lean formalization have not been completed.

## Problem and notation

A visible state is a permutation of `1,…,m,0^r`. `L` rotates the row left, `R` rotates it right, and `X` swaps its first two entries. Its distance `d(v)` is the minimum number of operations needed to reach the canonical row `(1,…,m,0^r)`. The sorting radius is the maximum of `d(v)` over visible states. It is the eccentricity of that **fixed canonical root**, not the diameter and not the distance to a freely chosen rotation or a distinguished-zero root.

For `m≥8` and `r≥2`, the open conjecture is `E_r(n)≤T_m(n)` with

\[
T_m(n)=\frac{m(m+1)}2+(r-1)(m-2)
=\binom n2-\frac{(r-1)(r+4)}2,\qquad n=m+r.
\]

For `m=8`, this specializes to

\[
T_8(n)=\frac{8\cdot9}{2}+(r-1)(8-2)=6n-18,\qquad n=8+r.
\]

The general conjecture remains open. Each result here fixes the order of the eight positive labels and the positions of selected zero blocks; it then quantifies over the stated positive block lengths.

## Why a finite word profile proves an infinite family

For one fixed label order and `k` selected gaps, replace each positive-length zero block by one zero. A **direct word** `w` sorts this unit-block state. Track those `k` zeros individually during `w`, and normalize the word by deleting zero–zero swaps and canceling adjacent inverse rotations. Let `s_j` count swaps of zero `j` with a positive label. Divide rotations into runs before, between, and after `X` letters. For run `t`, `g_{t,0}` is its signed number of rotations (`L=+1`, `R=-1`); `g_{t,j}` is the signed number that carry zero `j`, with a `+1` adjustment when the run ends at a swap with zero `j` on the left and a `−1` adjustment when the run begins after a swap with zero `j` on the right. These boundary terms account for the rotation pieces of the swap macros below. Define

\[
B(w)=\#X+\sum_t|g_{t,0}|,\qquad
\beta_j(w)=2s_j+\sum_t|g_{t,j}|.
\]

To expand block `j` from one zero to length `\ell_j`, replace a rotation carrying it by `\ell_j` rotations. A swap with that block on the left expands to `L^(\ell_j−1) X (RX)^(\ell_j−1)`; with the block on the right it expands to `X (LX)^(\ell_j−1) R^(\ell_j−1)`. Direct inspection shows that each macro exchanges the entire zero block with the same adjacent positive label as the unit swap. The internal swaps and rotations add `2s_j(\ell_j−1)` letters beyond the unit `X` letters. After joining boundary rotations to adjacent runs and canceling inverses, the expanded word still sorts to the canonical row and has length at most

\[
\#X+\sum_j2s_j(\ell_j-1)
 +\sum_t\left|g_{t,0}+\sum_jg_{t,j}(\ell_j-1)\right|
\le B(w)+\sum_j\beta_j(w)(\ell_j-1). \tag{1}
\]

The inequality is the triangle inequality applied to each rotation run. It holds for **every positive integer length vector**; the literal expansions in the verifier check the implementation on examples and are not an extrapolation argument.

For verified words `w_i`, choose rational weights `\lambda_i\ge0` summing to one. Write `\bar B=\sum_i\lambda_i B_i` and `\bar\beta_j=\sum_i\lambda_i\beta_{ij}`. For any length vector, at least one word has expanded length no greater than the weighted mean of the bounds in (1). That word has integer length. For `m=8`, `k` unit blocks have target `30+6k`, so

\[
\bar B<31+6k,\quad \bar\beta_j\le6\;(1\le j\le k)
\quad\Longrightarrow\quad
d(v)\le6n-18\text{ for every positive length vector}. \tag{2}
\]

The strict inequality is essential: it turns an average below the integer threshold `6n−17` into at least one word of length at most `6n−18`. Equations (1)–(2) use the established direct-word construction; the results below supply new exact profiles and mixtures for their named cases.

## Certificate A: every positive length in a six-block family

For `a,b,c,d,e,f≥1`, set

\[
v_6=0^a\,1\,3\,0^b\,2\,0^c\,4\,0^d\,6\,8\,0^e\,7\,0^f\,5.
\]

Its label order is `(1,3,2,4,6,8,7,5)` and retained gaps are `0,2,3,4,6,7` (case `k6-mask221-order731`). The following complete unit words replay to the canonical root. Each row lists the exact direct profile `(B;\beta_a,…,\beta_f)` and mixture weight.

| Origin | Weight | `B` | `(βa,βb,βc,βd,βe,βf)` | Complete unit word |
| --- | ---: | ---: | --- | --- |
| Frozen catalog | `3/19` | 48 | `(4,8,11,9,3,0)` | `LLXRXLLXLXRXRXRRRXLXLXLXLXLXLXLLXLXLLXRXRXRRRRRR` |
| Frozen catalog | `9/19` | 76 | `(7,1,2,5,11,9)` | `XRRXRXRRXRXLLXLLLXRXRXRRXLXLLXLLLXRXRXRXRXRRXRRRXLXLXLLXLLLLLLLLXLXLXLXLLXRR` |
| New direct word | `7/19` | 61 | `(5,11,9,6,0,3)` | `RXLXLXLXRXRXRRRXLXLXLXLXLXLXRXRXLLLLXRXRXLLLLXLXRRXLXRRXRRRRR` |

The weights sum to one and give

\[
\bar B=\frac{1255}{19}=66+\frac1{19}<67,
\qquad
\bar\beta=\left(\frac{110}{19},\frac{110}{19},6,6,
\frac{108}{19},\frac{102}{19}\right)\le(6,6,6,6,6,6).
\]

For `d_j=\ell_j−1` and `n=8+a+b+c+d+e+f`, the weighted mean in (1) is at most `1255/19+6Σd_j<67+6Σd_j`. Hence one expanded word has integer length at most `66+6Σd_j=6n−18`. Therefore **`d(v_6)≤6n−18` for all six positive block lengths**.

This certificate uses a direct word outside the frozen catalog plus deterministic all-cuts pool. The new word and all 29 direct reference columns are included in `certificates.json`.

## Certificate B: a conditional five-block family

For `a,b,c,d,e≥1`, set

\[
v_5=4\,0^a\,1\,0^b\,7\,0^c\,8\,5\,0^d\,6\,3\,2\,0^e.
\]

Its label order is `(4,1,7,8,5,6,3,2)` and retained gaps are `1,2,3,5,8` (case `k5-mask302-order15713`). The five verified support rows are:

| Origin | Weight | `B` | `(βa,βb,βc,βd,βe)` | Complete unit word |
| --- | ---: | ---: | --- | --- |
| Frozen pool | `3/40` | 56 | `(5,8,12,6,3)` | `XLXLXLLLLXRXLXLLXRXRXRRXLXLLLLXRXRXRXRXRXRXRRXRRRXLXLXLX` |
| Frozen pool | `2/5` | 61 | `(9,6,3,3,12)` | `RRRXLXRXRRRXLLXLXLXLXLLXLLXRXLLLXRXRXRRRXRRRRRXLXLXLXLXRXRXRX` |
| Frozen pool | `23/70` | 64 | `(2,5,8,9,0)` | `XLLXLLXRXRRXLXLXLLLLLXLLXRXRXRXRXRXRXLLLXLXRRXLXLLLXRXRXRXRXRXRR` |
| Frozen pool | `1/10` | 67 | `(1,2,5,12,3)` | `RXRRRXRXRXLLXLLLLLLXLLXRXLLLXLXLXLLXRXRXRXRRXLXLXLXLLLXRXRXRXRXRRXR` |
| New direct word | `27/280` | 50 | `(9,12,8,2,7)` | `XLXRRRXRXLXLXLXRRXRRRXRRXRXLXLXRXRRXLXRRRXRXRXRXLX` |

Their exact mixture is

\[
\bar B=\frac{1223}{20}=61+\frac3{20},\qquad
\bar\beta=(28/5,6,6,6,6).
\]

Here `n=8+a+b+c+d+e` and the target for unit lengths is 60. With `d_1=a−1` and `d_j=\ell_j−1`, the weighted bound is

\[
\frac{1223}{20}+\frac{28}{5}d_1+6\sum_{j=2}^{5}d_j
=61+6\sum_{j=1}^{5}d_j+\frac3{20}-\frac25d_1.
\]

If `a≥2`, the final surplus is at most `−1/4`; integrality then yields **`d(v_5)≤6n−18` for every `a≥2` and every positive `b,c,d,e`**. At `a=1`, this particular mixture does not reach the strict threshold. The full all-positive-length five-block family remains uncertified by it; this says nothing about the actual distance of its unit-block state. An older displayed mixture from the frozen pool reaches the same uniform inequality only for `a≥3`. Thus the improvement to `a≥2` is a **uniform-family mixture improvement**, not a claim that the new word is shorter at every individual state.

## What the exact duals establish

The obstructions in this section are about specified finite pools of direct-word profiles and a **single uniform mixture**. The inherited comparison profiles were materialized into complete direct words before these pools were frozen; the package replays and reprices each resulting column. These obstructions are not lower bounds on LRX distance. For any pool whose columns satisfy `B_i+Σ_j μ_j β_ij≥ν` with `μ_j≥0`, every mixture with `\bar\beta_j≤6` has `\bar B≥ν−6Σ_j μ_j`.

For Certificate A, all 29 direct columns in the frozen catalog plus deterministic all-cuts pool satisfy this inequality with

\[
\mu=(0,0,1,59/12,1/12,0),\qquad \nu=207/2.
\]

Consequently `\bar B≥135/2=67.5>67`: that pool cannot meet criterion (2) for this case. The added direct word has reduced cost `B+μ·β−ν=−4`, which crosses this finite-pool separating inequality and permits the displayed certificate.

For Certificate B, the 27 frozen direct columns satisfy

\[
B_i+\beta_{i1}+\frac57\beta_{i2}+\frac{47}{49}\beta_{i3}
+\frac23\beta_{i4}+\frac{50}{147}\beta_{i5}\ge\frac{4079}{49}.
\]

Thus every single mixture from those columns with slopes 2–5 at most 6 has `\bar B+\bar\beta_1≥3291/49>67`. It cannot certify **uniformly** the condition `a≥2` by this direct-mixture criterion. It can still supply a different word for a particular length vector; indeed a frozen word meets the numerical target at `(a,b,c,d,e)=(2,1,1,1,1)`.

The expanded five-block pool has 123 direct profiles (27 frozen and three further sets of 32). It also has a tight exact base dual for the constrained mixture with slopes 2–5 at most 6: multipliers `(0,11/5,1/2,19/20,3/4)` and intercept `1751/20` give `\bar B≥1223/20`. For further search in this **same linear program**, a new profile with `B+μ·β<1751/20` is necessary to lower that optimum; negative reduced cost alone is not a certificate. A full five-block result still needs a verified word construction and an exact mixture satisfying the strict bound for every positive length vector, or a different proof argument.

## Evidence and scope

The packaged verifier replays each complete unit word, recomputes the direct resources and mixtures with rational arithmetic, checks the three displayed dual certificates, and checks literal nonunit expansions. The all-length conclusions follow from (1), not from the finite expansion samples. A word replay proves an upper bound; neither it nor a failed search certifies shortest-path optimality. No global count of covered LRX states or families is inferred here. The full `m=8` radius claim and the general `m≥8` conjecture remain open.
