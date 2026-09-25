# corr-cert-260924 steps 1-3 report (2026-09-24)

Scope: protocol steps 1-3 are done. That covers the exact evaluator, the
identity validation, LP regeneration with rounding and exact re-check, and
canonical certificates with a pattern report. Steps 4-7 were not started.
Nothing was committed, no live API was called, and the trusted core is
unchanged (`python tools/orchestrator.py trusted` reports ok).

## Headline

- Every m from 4 to 16 has an exactly checked certificate with epsilon < 1,
  in all three families: plain, canon and sym. This independently reproduces
  the group's Theorem 1 range m = 4..16 as finite certificates. It says
  nothing about m > 16. The main conjecture remains open.
- The LP optimum is epsilon = 0 to within 3e-10 at every m. That is the
  smallest possible value, since E = 0 is attained at p_i = -i mod m. The
  positive epsilons are rounding artefacts from Q = 10^6.
- Exact epsilon = 0 certificates exist for m = 4, 5, 6, 7 (`certs-exact/`,
  Q = 1, 1, 2, 596). For m = 8, 9 they could not be recovered by
  rationalisation, and m >= 10 was not attempted.

## Step 1: identities (`validate_identities.py`, output `validate.json`)

All orders were enumerated for m = 4..8, and a seeded sample (seed 260924,
20000 orders) was checked for m = 9, 10. Zero failures were found for:
Lemma 2 (C, H and K identities), identity (4), the bijection of q_ab over b,
property (3), and C <= 4K + 2H. The definitions are consistent with the note.
Max E is 0 for m = 4..8, attained by exactly m orders: the rotations of
p_i = -i mod m. The sample maxima were -2 at m = 9 and -36 at m = 10; the
samples do not contain the equality order. The full E distributions are in
`validate.json`. Runtime was 5 s.

## Steps 2-3: LP (`search_lp.py`, log `search_log.jsonl`, console `search_run.log`)

Solver: scipy 1.16.1 `linprog(method="highs-ipm")` with crossover. This is a
system `python3` dependency on the search side only; the repo runtime stays
stdlib, and the checker `corrcert.py` is stdlib with exact ints and Fractions.
The protocol named `method="highs"`, but it was about 6x slower (m=12: 224 s
against 3 s for ipm) with the same LP value. `CORRCERT_LP_METHOD` switches it.
Rounding is to Q = 10^6 followed by the group's repair: first the triple rows
fix alpha, then the pair rows fix lambda.
The canon family minimises L1 subject to epsilon <= the plain rounded
epsilon. The sym family adds the reversal-symmetry equalities.
The checks count is always C(m,3)(m-1)(m-2) + C(m,2)(m-1). For m = 16 that is
117600 + 1800.

| m | checks | LP eps (Q=1) | plain rounded eps | ~ | group eps | ~ | canon eps | sym eps | exact eps=0 Q | LP s plain/canon/sym |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 42 | 0.0e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | 0 | 0 | 1 | 0.01/0.0/0.0 |
| 5 | 160 | 0.0e+00 | 0 | 0.00e+00 | 0 | 0.00e+00 | 0 | 0 | 1 | 0.01/0.0/0.01 |
| 6 | 475 | 1.1e-13 | 1/400000 | 2.50e-06 | 1/1200000 | 8.33e-07 | 7/2000000 | 11/3000000 | 2 | 0.01/0.02/0.03 |
| 7 | 1176 | 4.3e-13 | 1/218750 | 4.57e-06 | 13/3500000 | 3.71e-06 | 1/175000 | 7/1000000 | 596 | 0.06/0.06/0.15 |
| 8 | 2548 | 2.8e-13 | 51/8000000 | 6.37e-06 | 17/4000000 | 4.25e-06 | 37/4000000 | 7/800000 | not found | 0.09/0.19/0.18 |
| 9 | 4992 | 2.8e-13 | 11/1125000 | 9.78e-06 | 43/9000000 | 4.78e-06 | 11/750000 | 11/750000 | not found | 0.26/0.49/0.5 |
| 10 | 9045 | 6.8e-12 | 119/10000000 | 1.19e-05 | 87/10000000 | 8.70e-06 | 183/10000000 | 93/5000000 | not run | 0.59/1.19/1.14 |
| 11 | 15400 | -3.4e-13 | 87/5500000 | 1.58e-05 | 57/5500000 | 1.04e-05 | 17/687500 | 4/171875 | not run | 1.52/2.77/2.58 |
| 12 | 24926 | 2.7e-11 | 191/12000000 | 1.59e-05 | 49/4000000 | 1.22e-05 | 21/800000 | 83/3000000 | not run | 2.91/7.13/6.54 |
| 13 | 38688 | -2.5e-11 | 301/13000000 | 2.32e-05 | 1/62500 | 1.60e-05 | 37/1000000 | 487/13000000 | not run | 8.81/19.29/12.72 |
| 14 | 57967 | 2.2e-10 | 369/14000000 | 2.64e-05 | 267/14000000 | 1.91e-05 | 599/14000000 | 313/7000000 | not run | 12.58/43.44/25.33 |
| 15 | 84280 | 2.2e-11 | 61/1875000 | 3.25e-05 | 247/7500000 | 3.29e-05 | 157/3000000 | 261/5000000 | not run | 36.75/90.04/53.23 |
| 16 | 119400 | 3.7e-11 | 599/16000000 | 3.74e-05 | 301/8000000 | 3.76e-05 | 49/800000 | 249/4000000 | not run | 69.64/171.16/86.29 |

Re-check: every JSON in certs/, certs-canon/, certs-sym/ and certs-exact/ was
reloaded and re-verified by `corrcert.check_certificate`, with no scipy
involved. Epsilon matched and every run was ok. Four negative controls ran per
file: one alpha, one lambda and one mu coefficient pushed just past its
tightest slack, plus one float coefficient. All were rejected.

Discrepancies with the group: our plain rounded epsilons have the same order
as theirs (1e-6 to 4e-5). They are 1.0-3x larger for m = 6..14 and equal
within 1% for m = 15, 16. Both are pure rounding error on top of LP value 0;
the gap reflects which vertex is rounded. Neither is closer to 1. The canon
and sym epsilons are larger because L1 minimisation lands on a different
vertex before rounding.

## Symmetry check (before imposing)

E is invariant under relabel a -> m-1-a with negated positions: this held for
all orders at m <= 7. kappa shifts by a constant per pair, those constants sum
to 0 for m = 4..16, and the image of every plain certificate passes the exact
check with the same epsilon. The rounded sym certificates are exactly
symmetric only for m = 4, 5, because the per-row repair breaks exact symmetry.
The exact family is exactly symmetric for m = 4..7.

## Limitations

- The LP optima are floats. Epsilon = 0 is proved exactly only for m = 4..7.
- LP vertices are not unique, and all pattern observations in `PATTERNS.md`
  are single-vertex observations. No closed-form formula is claimed.
- The m = 9, 10 identity checks are samples, not complete enumerations.
- `lp-raw/` (3.7 MB) keeps float LP vectors for pattern work. It is not
  evidence.

## Files

corrcert.py, validate_identities.py, search_lp.py, patterns.py, THEOREM.md,
PATTERNS.md, PATTERNS_tables.md, validate.json, search_log.jsonl,
search_run.log, exact_run.log, certs/, certs-canon/, certs-sym/, certs-exact/,
lp-raw/, tests/test_search_corrcert.py (6 tests, under 0.1 s).

# Step 4: deterministic symbolic control (shared-parameter ansatz LP)

Script: `ansatz_lp.py`, which needs scipy on the search side. Diagnostics are
in `diag.py`, `diag_subsets.py` and `diag_dual.py`. Per-run JSON goes to
`ansatz/`, and summary lines to `ansatz_table.log`.

Method. Every certificate coefficient is an integer combination of shared
rational parameters theta: coefficient = sum over features f(q) of a
polynomial of degree <= d, with theta as its coefficients.
- Triple features are q, 1, and step and indicator functions at the kappa
  thresholds.
- mu_a(q) = y(a,m) q + v(a,m) plus bumps at q in {a, m-1-a, a+1, m-a}, with
  polynomial heights in (a, m).
- lambda_ab is a polynomial in (a, b, m).

One LP ties per-m certificate copies to theta by equalities and minimises
t = max_m epsilon(m) over the training range. t* < 1 means the ansatz holds
a proof for every training m.
For rationalisation, a second LP adds a margin of 1e-3 to every (5) and (6)
row, caps epsilon at 1/2 and minimises ||theta||_1. Theta is then rounded, to
a common grid of 1/D or by per-parameter continued fractions, and re-checked
exactly with `corrcert` on the training range. The holdout is checked exactly
from the end of training up to m = 20, stopping at the first failure.

Families:
- F1: linear potentials q and 1 only.
- F2: F1 plus the pair's own thresholds [q > v], [q < m-u], [q == v-u],
  [q == m-(v-u)] and [q >= m-(v-u)].
- F3: F2 with heights in the gaps (b-a, c-b, m) only.
- F4: F2 plus q times each step.
- F5: every role sees the thresholds of all three pairs of its triple
  ([q > x], [q < m-x] for x in a, b, c; [q == g], [q == m-g] for all gaps).
- F6: F5 plus q times each step.
- F7: F6 with separate parameters per unit-gap class ([b-a == 1], [c-b == 1]).

## Feasibility table (t* = min over theta of max epsilon; < 1 needed)

| family | deg | params | m=4..8 | m=4..10 | m=4..12 |
|---|---|---|---|---|---|
| F1 | 2 | 136 | 64.0 | 171.9 | 377.3 |
| F2 | 2 | 361 | 26.9 | 93.9 | 211.0 |
| F3 | 2 | 256 | 47.1 | 128.6 | 276.4 |
| F4 | 2 | 496 | 21.8 | 80.1 | 184.8 |
| F5 | 2 | 676 | 13.3 | 72.5 | 181.1 |
| F6 | 2 | 946 | 4.68 | 52.5 | 140.8 |
| F5 | 3 | 1550 | **0** (holdout: fails m=9) | not run | not run |
| F6 | 3 | 2180 | **0** (holdout: fails m=9) | 16.2 | not run |
| F7 | 2 | 3646 | **0** (holdout: fails m=9) | 14.6 | >= 14.6 (implied; run stopped) |

Allowing Q = m^k, so heights polynomial/m^k, did not help. F2 and F6 at
degree 2 on m=4..8 stay at 26.9 and 4.7 for k = 0, 1, 2. The binding
failure is already a single m (m=8), where per-m scaling is irrelevant.

## Holdout results for the feasible (family, range) cells

All three feasible cells (F5 d3, F6 d3 and F7 d2 on m=4..8) rationalised and
passed m = 4..8 exactly with epsilon about 0.5. Each failed at the first
holdout m = 9, with 1220, 1227 and 804 violated rows, violations of order 1
to 13 in Q = 1 units, and epsilon about 0.45 (so J was fine). These are
interpolation fits, not structure. No universal-lemma candidate exists, so
no FORMULA.md was written. The pipeline was also exercised on F2 d2 over
m = 4..6: t* = 0, grid rationalisation at Q = 10^6 passed exactly
(epsilon = 1000027/2000000 at m=4), and it failed at m = 7 with 230
violations.

Forced tightness held at every t* ~ 0 optimum. Max slack at the
equality-order rows was <= 4e-6 for F6 d3 and <= 1e-8 for the others,
as predicted.

## Where the ansatz lacks structure (packet for the engines)

1. The bottleneck is the triple functions. On m=4..8 with F4 d2, leaving the
   triple coefficients free per m while keeping the degree-2 ansatz for mu
   and lambda gives t* = 0. Freeing mu or lambda instead leaves
   t* = 14.5 or 18.9.
2. Single-m fits need the polynomial degree to grow with m. F2 at m=7 needs
   degree 4 (t* = 10.2, 0.11, 0 at degrees 2, 3, 4). m=8 also needs degree 4.
   At m=9 degree 5 gives 2.87, and m=10, 11 fail numerically. So heights are
   not low-degree polynomials in (a, b, c, m) with these q-features.
3. Freeing one class of triples on F6 d2 over m=4..10 (base t* = 52.5):
   | freed class | t* |
   |---|---|
   | b-a == 1 or c-b == 1 | **0** |
   | c-a <= m/2 | 1.14 |
   | a == 0 or c == m-1 | 7.95 |
   | interior | 11.6 |
   | a+c < m-1, or > m-1 | 11.1 |
   | c-a > m/2 | 13.1 |
   | b-a > 1 and c-b > 1 | 20.7 |
   | a == 0, or c == m-1 | 22.9 |
   | a+c == m-1 | 34.7 |
   Triples containing an adjacent label pair carry the structure that
   degree-2 polynomials cannot express. All other triples are fine with F6
   d2 through m = 10. F7 gives the unit-gap classes their own degree-2
   polynomials and still has t* = 14.6 on m=4..10. So the unit-gap triples
   need non-polynomial dependence on (a, c, m), or q-features beyond the
   thresholds used here. This is the target for the engines.
4. The dual certificates of infeasibility are in
   `ansatz/dual-F6-d2-m8.json` and `ansatz/dual-F2-d2-m7.json`. Mass spreads
   over 592 of 2548 rows at m=8, mirror-symmetric under a -> m-1-a. About 60%
   of the triple mass is on wrapping rows (q + t > m), and about a third is at
   the equality-order q = m-(b-a). The heaviest gap classes are (1,1), (1,2),
   (2,1) and (1,3).

Limitations: every cell is a float LP. "0" means t* <= 1e-9. The dual and
subset diagnostics are float and not certificates. The time used was well
under the 2 h box (about 75 min of LP time). t* only grows with the training
range, so a cell to the right of a failing cell must also fail.
