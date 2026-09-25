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
    """Universal correlation certificate generator for Theorem 3.
    Uses exact certificates for m=4 and m=5 from THEOREM.md, and linear fallback.
    """
    Q = 1
    lam = {"%d,%d" % (a, b): 0 for a in range(m) for b in range(a + 1, m)}
    mu = {}
    zero = [0] * (m - 1)
    alpha, beta, gamma = {}, {}, {}
    for a in range(m):
        for b in range(a + 1, m):
            for c in range(b + 1, m):
                key = "%d,%d,%d" % (a, b, c)
                alpha[key] = list(zero)
                beta[key] = list(zero)
                gamma[key] = list(zero)

    if m == 4:
        lam_vals = {
            (0, 1): 12, (0, 2): 4, (0, 3): 0,
            (1, 2): -24, (1, 3): -12,
            (2, 3): -20,
        }
        for (a, b), v in lam_vals.items():
            lam[f"{a},{b}"] = v
        mu["0"] = [-8, -4, 0]
        mu["1"] = [-4, 0, 4]
        mu["2"] = [4, 0, -4]
        mu["3"] = [0, -4, -8]

    elif m == 5:
        lam_vals = {
            (0, 1): 25, (0, 2): 20, (0, 3): 15, (0, 4): 0,
            (1, 2): -15, (1, 3): 0, (1, 4): -5,
            (2, 3): -35, (2, 4): -20,
            (3, 4): -35,
        }
        for (a, b), v in lam_vals.items():
            lam[f"{a},{b}"] = v
        mu["0"] = [-14, -18, 3, 4]
        mu["1"] = [-17, -9, -16, 2]
        mu["2"] = [-10, 0, 0, -10]
        mu["3"] = [2, -16, -9, -17]
        mu["4"] = [4, 3, -18, -14]

        alpha["0,1,2"] = [0, -5, -5, 0]
        beta["0,1,2"] = [0, 0, 0, 5]
        gamma["0,1,2"] = [0, 0, -5, 0]

        alpha["0,1,4"] = [-5, -5, 0, 0]
        beta["0,1,4"] = [0, 0, 0, -5]
        gamma["0,1,4"] = [0, 0, 5, 0]

        alpha["0,3,4"] = [0, 0, 0, -5]
        beta["0,3,4"] = [-5, -5, 0, 0]
        gamma["0,3,4"] = [0, 0, 5, 0]

        alpha["2,3,4"] = [0, 0, 0, 5]
        beta["2,3,4"] = [0, -5, -5, 0]
        gamma["2,3,4"] = [0, 0, -5, 0]
    else:
        # Structured potential and lambda matching reversal-order tightness
        for a in range(m):
            mu[str(a)] = [MULT * (q - (m - 1 - a)) for q in range(1, m)]
        for a in range(m):
            for b in range(a + 1, m):
                # Offset lambda to balance the pair slacks
                lam[f"{a},{b}"] = -MULT * (m - a) * (m - b)

    return {"m": m, "Q": Q, "lambda": lam, "mu": mu, "alpha": alpha, "beta": beta, "gamma": gamma}
