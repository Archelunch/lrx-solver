# Symbolic-fit control: candidate coefficient families

Purpose: the deterministic control for step 4. If any family below fits
the LP certificates and re-checks exactly for m = 4..12, then passes the
holdout m = 13..20, the lemma candidate was found without an engine.

## Structural observation (from the theorem, not from data)

Triple condition (5): alpha(q) + beta(t) + gamma((q+t) mod m) <= 0 for
q + t != m. Pure linear potentials
  alpha(q) = x q + c1,  beta(t) = x t + c2,  gamma(s) = -x s + c3
give alpha + beta + gamma = (c1+c2+c3) + x m [q+t > m], so (5) holds iff
c1+c2+c3 <= 0 and c1+c2+c3 + x m <= 0. This linear family is exactly what
absorbs the linear-in-q part of kappa (the K identity). The nonlinear parts
of kappa are the indicators [q > b], [q < m-a], [q == b-a] from f_ab and H.
So any universal certificate should be: linear potentials plus bump terms
concentrated at those indicator thresholds.

## Families to fit, in order

F1. Linear potentials only: x_abc, c1, c2, c3 per triple; lambda_ab and
    mu_a(q) with mu_a(q) = y_a q + v_a + bumps at q in {a, m-1-a, ...}.
    Fit x, y, v, c as polynomials of degree <= 2 in (a, b, c, m) with
    rational coefficients (exact least squares over the canonical LP
    solutions), then re-check (5)-(7) exactly per m.
F2. F1 plus step functions: alpha_abc(q) += s1 [q > b] + s2 [q < m-a]
    + s3 [q == b-a] and the analogous thresholds for beta (pair b,c) and
    gamma (pair a,c), with step heights polynomial in (a,b,c,m).
F3. F2 with heights depending only on gaps (b-a, c-b, m) (translation
    structure), and separately on (a, b, c) mod reversal a -> m-1-a.
F4. Piecewise-linear in q with breakpoints at the thresholds above.

## Procedure

1. Take canonical certificates (min-L1, reversal-symmetric) for m = 4..12.
2. For each family, fit exactly (Fractions) on m = 4..10, predict m = 11, 12,
   re-check exactly. Report per m: fits / passes / first violation.
3. A family that passes m = 4..12 is frozen; holdout m = 13..20 evaluated once.
4. Never accept a numeric pass without the exact re-check; never repair a
   failing prediction by hand.

If every family fails at m = 11 or 12, the residual structure (which
triples, which q) becomes the packet for the engines in step 5.
