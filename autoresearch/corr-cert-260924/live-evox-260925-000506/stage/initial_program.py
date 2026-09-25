"""Seed candidate for corr-cert-260924: the F1 linear-potential family from
FIT-SPEC.md ("linear potentials only ... mu_a(q) = y_a q + v_a ... zero
bumps"), with triple functions identically zero (the x=0, c1=c2=c3=0 point of
the linear family in THEOREM.md's structural note, which always satisfies
(5) with equality 0<=0) and mu_a(q) generalizing THEOREM.md's exact m=4
certificate (mu_0=4(q-3), mu_1=4(q-2), mu_2=-4(q-2), mu_3=-4(q-1) at Q=1) by
the single formula mu_a(q) = 4*(q - (m-1-a)) for every a, not only the
reversal-symmetric half. This is a literal, honest first guess, not a fit:
FIT-SPEC.md is explicit that no closed form is established, and PATTERNS.md
shows mu_a(q) is not linear in q for m >= 5. It is expected to score well
only at m = 4 (where it reduces to the group's exact certificate) and is
reported here, unmodified, together with its real corr_evaluator score for
m = 4..12 -- it is not hand-tuned to pass.

Stdlib only. Output is the JSON-safe encoding documented in
integrations/corr_task.py (encode_cert): lambda/alpha/beta/gamma keyed by
comma-joined ints "a,b" / "a,b,c", mu keyed by "a".

MULT is the one tunable knob (search-and-replace target for mock proposers
in offline smokes; a live model may edit it too): the slope of mu_a(q) in q.
"""

MULT = 4


def coefficients(m):
    Q = 1
    lam = {"%d,%d" % (a, b): 0 for a in range(m) for b in range(a + 1, m)}
    mu = {str(a): [MULT * (q - (m - 1 - a)) for q in range(1, m)] for a in range(m)}
    zero = [0] * (m - 1)
    alpha, beta, gamma = {}, {}, {}
    for a in range(m):
        for b in range(a + 1, m):
            for c in range(b + 1, m):
                key = "%d,%d,%d" % (a, b, c)
                alpha[key] = list(zero)
                beta[key] = list(zero)
                gamma[key] = list(zero)
    return {"m": m, "Q": Q, "lambda": lam, "mu": mu, "alpha": alpha, "beta": beta, "gamma": gamma}
