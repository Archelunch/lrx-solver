# Conditional all-length bound from one development mixture

For the frozen development arrangement `k5-mask302-order15713`, the [five frozen direct-word profiles and exact weights](sol-beam-k5-allcuts64-conditional-support.json) from the stronger all-cuts beam have weighted base

\[
B=\frac{1223}{20}=61+\frac{3}{20}
\]

and weighted slopes

\[
(\gamma_1,\ldots,\gamma_5)=\left(\frac{28}{5},6,6,6,6\right).
\]

Let the five retained zero-block lengths be \(\ell_j\ge1\), and put \(d_j=\ell_j-1\). For each support word, the general direct-word triangle expansion gives a complete LRX word of length at most its base plus \(\sum_j\gamma_jd_j\). The weighted average of these five upper bounds is

\[
B+\sum_j\gamma_jd_j
=61+6\sum_j d_j+\frac{3}{20}-\frac{2}{5}d_1.
\]

If \(\ell_1\ge2\), then \(d_1\ge1\) and the final surplus is at most \(-1/4<0\). Hence at least one of the five expanded words has integer length **strictly below** \(61+6\sum_jd_j\), so its length is at most \(60+6\sum_jd_j=6n-18\), where \(n=8+\sum_j\ell_j\). This is an infinite proper subfamily: the first retained block has length at least 2; the other four may have any positive lengths. For all blocks of length 1, the inequality fails by \(3/20\); it does not certify the missing unit-block family.

The frozen incumbent's displayed mixture has \(B=24149/392\), slopes \((2179/392,6,6,6,6)\), and surplus \((237-173d_1)/392\). That **same fixed mixture** reaches the criterion only for \(\ell_1\ge3\). More strongly, an exact dual with multipliers \((5/7,47/49,2/3,50/147)\) for slopes 2–5 and intercept \(4079/49\) checks nonnegative reduced cost on all 27 fixed direct columns. It proves every **single uniform mixture** from that frozen pool with slopes 2–5 at most 6 has \(B+\gamma_1\ge3291/49>67\), so none gives this uniform conditional inequality at \(\ell_1=2\). It does not rule out choosing different old words for different integer length vectors, and makes no claim about the literature or all possible constructions. For example, one old word already satisfies the numerical target at lengths \((2,1,1,1,1)\).

The [standalone checker](sol-beam-k5-allcuts64-conditional-check.py) recomputes source/evaluation hashes, direct resources and unit replay for every support word, exact weights/slopes, the 27-column dual, and 15 literal nonunit expansions across three length vectors. Its literal examples test the expansion; the arbitrary-length conclusion uses the general direct-word macro and triangle argument, which has not been newly formalized here. Run:

```sh
python autoresearch/loop-260924-protocol/sol-beam-k5-allcuts64-conditional-check.py
```
