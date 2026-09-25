# corr-cert-260924: universal coefficients for the correlation certificate

Started 2026-09-24. Goal: a formula for the Theorem 3 certificate
coefficients (lambda_ab, mu_a(q), alpha_abc(q), beta_abc(q), gamma_abc(q))
valid for every m, proving C <= 4K + 2H beyond the group's numeric range
m <= 16. Source: the group's note "Корреляционная оценка: тройные
сертификаты" (2026-09-24), definitions reproduced in `THEOREM.md`.
The group's coefficient files are NOT available; certificates are
regenerated here by LP (system scipy, search side only; the checker is
stdlib and exact).

Success levels
1. System works: an engine yields a coefficient program passing m = 4..12
   (development) that the controls (deterministic fit, random mutation,
   sequential refinement) do not reach.
2. Useful: the same program passes holdout m = 13..20, evaluated once.
3. Proved: symbolic proof of (5)-(7) from the formula, by human or Lean.

Kill conditions: no program passing m >= 10 after 150 proposals per arm;
or the deterministic fit already passes holdout (engines then skipped).
Budget ceiling $25, timebox one day. Controls and three seeds per engine
before any comparative statement.

Steps: (1) exact evaluator + brute-force validation of the identities;
(2) LP regeneration of certificates m = 4..12+ with rounding and repair,
exact re-check; (3) canonicalized certificates and pattern report;
(4) deterministic symbolic fit control; (5) engines, only if (4) fails;
(6) one-shot holdout and independent re-check; (7) report.
