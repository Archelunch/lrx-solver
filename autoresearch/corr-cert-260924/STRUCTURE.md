# Structure hunt on exact small-m certificates (2026-09-24, about 60 min)

Search side (scipy). Scripts: `structure.py`, `kscan.py`, `tightface.py`.
Certificates are in `certs-structure/`, and every one there passed the exact
`corrcert` check. "LP epsilon" is a float value, and "exact" means a
Fraction check of (5)-(7).

## 1. Support of the triple terms: the needed support grows with m

Minimum LP epsilon when every triple coefficient outside the support is
forced to 0 (`structure_support*.log`, `structure_roles.log`, `kscan.log`):

| support | epsilon ~ 0 for | first failure |
|---|---|---|
| none (pairs only) | m = 4 | m=5: 2 |
| consecutive (a, a+1, a+2) | m <= 5 | m=6: 2 |
| b-a = 1, i.e. (a, a+1, c) | m <= 10 | m=11: 3.31, m=16: 93.7 |
| b-a = 1 or c-b = 1 | m <= 12 | m=13: 1.24, m=14: 11.3 |
| b-a <= 2 | m <= 14 | m=15: 7.54 |
| drop any one role of alpha, beta, gamma | never | same as "none" |

Smallest k such that the triples with b-a <= k suffice (float LP; the scan was stopped at the time box, with m = 19 needing k > 2 and m = 20 not run):

| m | k |
|---|---|
| 5..10 | 1 |
| 13 | 2 |
| 14 | 2 |
| 15 | 3 |
| 16 | 4 |
| 17 | 5 |
| 18 | 6 |

- The reduced problem works only for small m. "Triples (a, a+1, c)" gives an
  exact epsilon = 0 certificate for m = 5..9 (exact-checked, below) and LP
  epsilon 0 at m = 10, but fails from m = 11.
- The needed gap width grows quickly, from k = 2 at m = 14 to 6 at m = 18.
  So no fixed-width "adjacent-label" lemma exists in this certificate
  format.
- Within (a, a+1, c) for m >= 9, no tested proper subclass suffices. The
  subclasses tried were split by c-a vs m/2, c = m-1, a = 0, a+c vs m-1, and
  left half.
- A triple needs all three of alpha, beta and gamma. Dropping one reduces
  it to separable functions, which contribute nothing.

## 2. Clean gauge and small Q

- **Minimal L-infinity** with epsilon <= 0, support b-a = 1, Q = 1:
  L-inf*(m) = 12.62, 21.5, 33.5, 48, 65, 84.5 for m = 5..10. For
  m = 6..10 this equals (5m^2 - 17m + 8)/4 exactly. The formula was fitted
  on m = 6..9 and predicted m = 10 (float LP values). On full support the
  values 9.16, 13.6, 18.5, 24.3, 31.2 for m = 5..9 have no clean form.
- **Exact epsilon = 0 certificates on the b-a = 1 support exist for
  m = 5..9.** They were recovered by exact Gaussian elimination on the LP's
  tight rows and are stored in `certs-structure/T1-m<m>.json`. Their Q is
  huge (12 at m = 6, but 10^10 to 10^22 for m = 7..9), because the L1 point
  is not a vertex and 80 to 130 columns are free. The full-support exact
  certificates exist for m = 5..7 (`all-m<m>.json`). At m = 8, 9 the
  recovered point had 7 and 10 violations.
- **Small Q scan** (Q = 1..2m: round Q times the LP point, group repair,
  exact check; heuristic, so these are upper bounds, and no ILP was run):

| m | support b-a=1: smallest proving Q (epsilon) | epsilon = 0 at Q | full support: smallest proving Q (epsilon) |
|---|---|---|---|
| 5 | 2 (0) | 2, 4, 6, 8, 10 | 1 (0) |
| 6 | 2 (2/3) | 4, 8, 12 | 3 (8/9) |
| 7 | 2 (5/7) | none <= 14 | 4 (23/28) |
| 8 | 3 (5/6) | none <= 16 | 7 (47/56) |
| 9 | 4 (11/12) | none <= 18 | 8 (71/72) |
| 10 | 6 (9/10) | none <= 20 | 11 (109/110) |

  Q = m does not give epsilon = 0 uniformly. Small-Q integer certificates
  that prove the bound (epsilon < 1) do exist, and the restricted support
  needs a smaller Q than the full support.
- **By eye (tables below):** mu_a(q) is not a simple piecewise-linear
  function in these gauges. Many triples are "linear potential plus 1-2
  corrections". At m = 6, triple (0,1,2) has alpha, beta and gamma equal to
  plus or minus 44(q - const) on most q. The m = 6 triple (0,1,4) is a pure
  period-2 pattern of +-36. The m = 5 window shape (+-5 on width-2 windows)
  does not persist cleanly.

## 3. Rows tight on the whole optimal face

Twelve random optimal vertices were averaged under epsilon <= 0; a row is
listed if its average slack is < 1e-7. See `tightface_all.log` and
`tightface-all.json`.

| m | tight pair rows | of which forced | tight triple rows (support) | forced |
|---|---|---|---|---|
| 5 | 28 / 40 | 10 | 14 / 120 | 10 |
| 6 | 50 / 75 | 15 | 57 / 400 | 20 |
| 7 | 105 / 126 | 21 | 106 / 1050 | 35 |
| 8 | 164 / 196 | 28 | 279 / 2352 | 56 |

- Most pair rows (6) are tight on the whole face, 84% at m = 8. So in every
  optimal certificate, P_ab(q) = kappa_ab(q) for most (a, b, q). For large
  b-a almost every q is tight; small b-a is mixed.
- **The tight set is not a function of (b-a, q) alone.** Many (d, q) cells
  are partially tight, for example 2/7 pairs at d = 1, q = 1 when m = 8.
- Extra tight triple rows are about 10% of triple rows. Most are wrapping
  (q + t > m) with q or t at its equality-order value.

## 4. Smallest conjecture to try (CONJECTURE, not proved)

The unit-gap and Q = m conjectures are refuted: b-a = 1 fails at m = 11,
unit-gap at m = 13, and Q = m does not give epsilon = 0 at m >= 7. What
survives, for every m tested, is:

> **Conjecture (triple relaxation is exact).** For every m >= 4 the LP
> (5)-(6) has optimum epsilon = 0. Equivalently, the triple-marginal
> relaxation of max E over circular orders is tight, and a rational
> certificate with epsilon = 0 exists. Proved (exact) for m = 4..9, where
> m = 8, 9 use the b-a = 1 support. Float LP evidence covers m = 10..18,
> with optimum at most 3e-10 in magnitude.

A proof cannot use a fixed-width label-local support, since the width grows
with m. A more promising route is the pair side: since most pair rows are
tight, define lambda and mu so that P_ab(q) = kappa_ab(q) holds as an
identity outside a small explicit set. Then prove (5) for the triples forced
by that choice. Alternatively, prove the dual statement: every
triple-consistent "pseudo-distribution" of the q_ab has E <= 0.

## Exact tables in the best small-Q gauge found

### m = 6, Q = 4, support b-a = 1, epsilon = 0 (exact check: 475 rows ok)

lambda_ab (row a, col b):

| a\b | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 0 |  | -502 | 0 | 0 | -87 | 67 |
| 1 |  |  | -524 | 0 | -132 | -10 |
| 2 |  |  |  | -118 | 0 | -57 |
| 3 |  |  |  |  | -746 | 0 |
| 4 |  |  |  |  |  | -268 |

mu_a(q) (row a, col q):

| a\q | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 0 | 0 | -48 | 39 | 0 | 198 |
| 1 | 61 | -103 | 0 | -95 | 95 |
| 2 | -54 | 28 | 65 | 36 | 16 |
| 3 | 126 | 120 | 9 | 0 | -12 |
| 4 | 145 | 83 | 0 | 91 | -25 |
| 5 | -27 | -51 | 0 | -111 | -129 |

Triples (a, a+1, c): alpha(q), beta(q), gamma(q) for q = 1..m-1:

| triple | alpha | beta | gamma |
|---|---|---|---|
| (0, 1, 2) | [-104, -132, -88, -44, 0] | [28, 0, 44, 88, 132] | [0, -44, -88, -132, 16] |
| (0, 1, 3) | [-237, -477, -393, -273, -153] | [141, 117, 153, 105, 225] | [36, 0, 48, -72, 132] |
| (0, 1, 4) | [0, 36, 0, -36, 0] | [-36, 0, -36, 0, -36] | [0, 36, 0, -36, 0] |
| (0, 1, 5) | [-194, -328, -174, -308, -154] | [174, 40, 134, 0, 154] | [114, 20, 154, 0, 110] |
| (1, 2, 3) | [-204, -264, -216, -240, -192] | [0, 204, 252, 192, 240] | [-12, -156, 0, -48, 12] |
| (1, 2, 4) | [-247, -247, -331, -331, -247] | [247, 163, 247, 247, 163] | [84, 0, 0, 0, 0] |
| (1, 2, 5) | [-44, 0, 44, -44, 0] | [0, 44, 88, 0, 44] | [-44, -88, 0, -44, -256] |
| (2, 3, 4) | [-176, -118, -228, -170, -112] | [0, 118, -4, 54, 112] | [-150, 116, 58, 0, 110] |
| (2, 3, 5) | [56, 0, 172, 224, 168] | [-112, -168, -224, -280, -336] | [0, 56, 112, -60, -112] |
| (3, 4, 5) | [-485, -381, -433, -461, -357] | [4, -168, -76, 28, 0] | [381, 433, 329, 357, 457] |

### m = 7, Q = 4, support b-a = 1, epsilon = 1/2 (exact check: 1176 rows ok)

lambda_ab (row a, col b):

| a\b | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| 0 |  | 111 | 133 | 133 | 90 | 63 | 10 |
| 1 |  |  | -20 | -1 | 9 | -27 | -31 |
| 2 |  |  |  | -137 | -134 | -67 | -134 |
| 3 |  |  |  |  | -136 | -134 | -134 |
| 4 |  |  |  |  |  | -135 | -134 |
| 5 |  |  |  |  |  |  | -134 |

mu_a(q) (row a, col q):

| a\q | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 0 | -132 | -79 | -20 | 52 | 134 | 134 |
| 1 | -64 | -88 | -36 | -32 | 21 | 95 |
| 2 | -134 | -134 | -15 | -48 | 19 | 52 |
| 3 | -134 | -108 | -48 | -131 | -134 | -57 |
| 4 | -134 | -102 | -134 | -134 | -91 | -134 |
| 5 | -134 | -134 | -134 | -134 | -126 | -134 |
| 6 | -134 | -110 | -67 | -134 | -134 | -134 |

Triples (a, a+1, c): alpha(q), beta(q), gamma(q) for q = 1..m-1:

| triple | alpha | beta | gamma |
|---|---|---|---|
| (0, 1, 2) | [-2, -64, -76, -2, 12, 0] | [0, 10, -2, -14, 0, 74] | [-10, 2, -72, -86, -74, -12] |
| (0, 1, 3) | [-1, -1, -25, -17, -39, 70] | [0, -31, -24, -45, 63, 25] | [-39, -47, -26, -134, -96, -63] |
| (0, 1, 4) | [0, 0, 0, 0, 0, 0] | [0, 0, 0, 0, 0, 0] | [0, 0, 0, 0, 0, 0] |
| (0, 1, 5) | [-26, -13, -13, 0, 13, 0] | [0, 0, 13, 0, -13, -26] | [-26, -13, 0, 13, 0, -13] |
| (0, 1, 6) | [-96, -75, -134, -94, 11, 32] | [123, -32, -11, 16, -43, -22] | [0, -27, -48, 11, -29, -134] |
| (1, 2, 3) | [0, 0, 0, -67, 0, 67] | [0, 0, 0, -67, 0, 67] | [-67, -67, 0, -67, -134, 0] |
| (1, 2, 4) | [-35, 0, -19, 0, -19, 10] | [0, -19, 16, 39, -29, 0] | [-39, -26, -49, 19, -16, -39] |
| (1, 2, 5) | [-34, -17, -17, -1, 0, 17] | [-17, -1, 0, 17, -17, -34] | [-17, -17, -34, 0, 17, 0] |
| (1, 2, 6) | [-49, -32, -28, -1, -1, 30] | [29, 33, -50, -33, -29, -2] | [-63, 19, 2, -2, -29, -33] |
| (2, 3, 4) | [-12, -4, 4, -16, -8, 0] | [0, 0, 35, 43, 51, 59] | [-56, -64, -43, -51, -59, -40] |
| (2, 3, 5) | [-86, -49, -1, 36, 13, 5] | [-22, 16, 64, -6, -28, -37] | [-78, -70, 0, 22, -16, -64] |
| (2, 3, 6) | [-87, -101, -46, 23, 58, 78] | [45, 31, 51, -134, -114, -78] | [-111, -131, 55, 0, -69, -104] |
| (3, 4, 5) | [-33, -27, -16, -124, -22, -1] | [0, 44, 0, 0, 32, 134] | [-108, -119, -11, -113, -134, 0] |
| (3, 4, 6) | [0, 0, 16, 0, 0, 95] | [39, 0, -56, -56, 39, 0] | [-95, -39, -39, -134, -95, -39] |
| (4, 5, 6) | [-6, -21, -84, -37, 8, 56] | [0, 0, -62, -15, 30, 78] | [-57, 6, -41, -86, -134, -24] |


