# Correlation bound via triple certificates

Source: the group's note "Корреляционная оценка: тройные сертификаты"
(2026-09-24). This file restates its definitions and claims in English with the
note's formula numbers. Theorem 1 and the numeric epsilons are the group's
results. Everything here for general m is open unless a certificate for that m
passes the exact checker `corrcert.py`.

## Definitions

Let p = (p_0, ..., p_{m-1}) be a permutation of 0..m-1, read as a circular
order; position indices are taken mod m.

- u_s = #{1 <= j < m : p_{s+j} < j},  U_s = 2 u_s - m + 1,  w_s = 2 p_s - m + 1.
- C = sum_s w_s U_s,  V = sum_s U_s^2.
- H = #{i < j : p_i - i == p_j - j (mod m)}.
- K = number of triples i < j < k with positive circular orientation:
  (p_j - p_i) mod m < (p_k - p_i) mod m.

**Theorem 1 (group; certified numerically for 4 <= m <= 16).**
C <= 4K + 2H for every circular order p.

## Pair coordinates

Let z_a be the position of label a. For 0 <= a < b < m put
q_ab = (z_b - z_a) mod m in {1..m-1} and q_ba = m - q_ab. Define

    f_ab(q) = 2(2a - m + 1) [q > b] + 2(2b - m + 1) [q < m - a].

**Lemma 2.**

    C = sum_{a<b} f_ab(q_ab),
    H = sum_{a<b} [q_ab == b - a],
    K = C(m,3) - (1/m) sum_{a<b} (m - 2(b - a)) q_ab.

For fixed a, the values q_ab over b != a run through 1..m-1 exactly once.
For a < b < c:

    q_ac = (q_ab + q_bc) mod m   and   q_ab + q_bc != m.                    (3)

## Certificate

Let E := C - 4K - 2H and

    kappa_ab(q) = -m f_ab(q) - 4(m - 2(b - a)) q + 2m [q == b - a].

Then

    m E = -sum_{a<b} kappa_ab(q_ab) - 4m C(m,3).                           (4)

Certificate data: a positive integer Q; integers lambda_ab (a < b);
mu_a(q) (0 <= a < m, 1 <= q < m); and for each triple a < b < c integer
functions alpha_abc(q), beta_abc(q), gamma_abc(q) on 1 <= q < m.

Triple conditions. For all a < b < c and all q, t in 1..m-1 with q + t != m:

    alpha_abc(q) + beta_abc(t) + gamma_abc((q + t) mod m) <= 0.            (5)

Pair conditions. For each a < b and each q:

    P_ab(q) := lambda_ab + mu_a(q) + mu_b(m - q)
               - sum_{c>b} alpha_abc(q) - sum_{c<a} beta_cab(q)
               - sum_{a<c<b} gamma_acb(q)   <=   Q kappa_ab(q).            (6)

Value:

    J = sum_{a<b} lambda_ab + sum_a sum_q mu_a(q),
    epsilon = -J / (Q m) - 4 C(m,3).                                       (7)

**Theorem 3.** If (5) and (6) hold, then E <= epsilon for every circular
order. E is an integer, so epsilon < 1 gives C <= 4K + 2H.

Proof sketch (checked while implementing). Sum (6) over pairs at q = q_ab.
The mu terms sum to sum_a sum_q mu_a(q) by the bijection in Lemma 2. Every
triple term appears once with q_ab, q_bc, q_ac, so by (3) and (5) the triple
terms contribute a nonnegative amount. Hence J <= Q sum kappa_ab(q_ab), and (4)
gives E <= epsilon.

## Group's numeric results (Q = 1000000)

| m | epsilon | m | epsilon |
|---|---|---|---|
| 4 | 0 | 11 | 57/5500000 |
| 5 | 0 | 12 | 49/4000000 |
| 6 | 1/1200000 | 13 | 1/62500 |
| 7 | 13/3500000 | 14 | 267/14000000 |
| 8 | 17/4000000 | 15 | 247/7500000 |
| 9 | 43/9000000 | 16 | 301/8000000 |
| 10 | 87/10000000 | | |

Their LP was solved in floating point. Coefficients were rounded to
denominator Q and then repaired: for each triple, the largest positive
violation of (5) was subtracted from all of its alpha(q); then for each pair,
the largest positive violation of (6) was subtracted from lambda_ab.

## Observations made here (not in the note)

- Equality E = 0 holds at the reversed order p_i = -i mod m for every m
  tested (K = 0 there). So no certificate can reach epsilon < 0, and every
  LP optimum is epsilon >= 0.
- Reversal symmetry. Relabel a -> m-1-a and negate positions. This maps pair
  (a, b) to (m-1-b, m-1-a) with the same q, swaps the alpha and beta roles of a
  triple, keeps gamma, and sends mu_a(q) to mu_{m-1-a}(m-q). kappa changes by a
  constant per pair, absorbed into lambda. See `search_lp.py`.
