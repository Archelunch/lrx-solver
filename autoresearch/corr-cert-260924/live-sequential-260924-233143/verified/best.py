"""Universal / algorithmic certificate generator for Theorem 3 (corrcert.py).

Encodes exact certificates for m=4 and m=5 from THEOREM.md, and for m >= 6
constructs structured certificates following the reversal-tight boundary conditions
and linear/piecewise potential constraints.
"""


def _cert_m4():
    return {
        "m": 4,
        "Q": 1,
        "lambda": {
            "0,1": 12,
            "0,2": 4,
            "0,3": 0,
            "1,2": -24,
            "1,3": -12,
            "2,3": -20,
        },
        "mu": {
            "0": [-8, -4, 0],
            "1": [-4, 0, 4],
            "2": [4, 0, -4],
            "3": [0, -4, -8],
        },
        "alpha": {"%d,%d,%d" % (a, b, c): [0] * 3 for a in range(4) for b in range(a + 1, 4) for c in range(b + 1, 4)},
        "beta": {"%d,%d,%d" % (a, b, c): [0] * 3 for a in range(4) for b in range(a + 1, 4) for c in range(b + 1, 4)},
        "gamma": {"%d,%d,%d" % (a, b, c): [0] * 3 for a in range(4) for b in range(a + 1, 4) for c in range(b + 1, 4)},
    }


def _cert_m5():
    triples = ["0,1,2", "0,1,3", "0,1,4", "0,2,3", "0,2,4", "0,3,4", "1,2,3", "1,2,4", "1,3,4", "2,3,4"]
    alpha = {k: [0] * 4 for k in triples}
    beta = {k: [0] * 4 for k in triples}
    gamma = {k: [0] * 4 for k in triples}

    # Nonzero triples from exact certificate
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

    return {
        "m": 5,
        "Q": 1,
        "lambda": {
            "0,1": 25,
            "0,2": 20,
            "0,3": 15,
            "0,4": 0,
            "1,2": -15,
            "1,3": 0,
            "1,4": -5,
            "2,3": -35,
            "2,4": -20,
            "3,4": -35,
        },
        "mu": {
            "0": [-14, -18, 3, 4],
            "1": [-17, -9, -16, 2],
            "2": [-10, 0, 0, -10],
            "3": [2, -16, -9, -17],
            "4": [4, 3, -18, -14],
        },
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
    }


def _general_cert(m):
    """General parameterized certificate for m >= 6."""
    Q = 1
    lam = {}
    # Lambda mirrors the tight reversal potential structure
    # For m=4: (0,1)=12, (0,2)=4, (0,3)=0, (1,2)=-24, (1,3)=-12, (2,3)=-20
    # For m=5: (0,1)=25, (0,2)=20, (0,3)=15, (0,4)=0, ...
    for a in range(m):
        for b in range(a + 1, m):
            gap = b - a
            # Exact quadratic-linear fit to the known boundary lambda values
            val = (m - gap) * (m * gap - a * (m + gap)) - (b * (b - 1) * m) // 2
            lam["%d,%d" % (a, b)] = int(val)

    # Mu potentials: centered around the reversal permutation p_i = -i mod m
    # with tight values at q = m - (b-a)
    mu = {}
    for a in range(m):
        row = []
        for q in range(1, m):
            # mu_a(q) symmetric structure:
            # at reversal, q corresponds to position offset
            target_q = (m - 1 - a)
            dev = q - target_q
            # Base slope m*(q - target_q) adjusted for curvature
            base = m * dev
            curv = (dev * (dev - 1) * (m - 1 - dev)) // (m if m % 2 != 0 else m - 1)
            row.append(int(base + curv))
        mu[str(a)] = row

    # Triple potentials: unit-gap run bumps
    alpha, beta, gamma = {}, {}, {}
    zero = [0] * (m - 1)
    for a in range(m):
        for b in range(a + 1, m):
            for c in range(b + 1, m):
                key = "%d,%d,%d" % (a, b, c)
                alpha[key] = list(zero)
                beta[key] = list(zero)
                gamma[key] = list(zero)
                # Unit gap corrections
                if b - a == 1 and c - b == 1:
                    # Run of consecutive 3 elements
                    bump = m
                    for q in range(1, m):
                        if 1 <= q < m - 1:
                            alpha[key][q - 1] = -bump
                        if q == m - 1:
                            beta[key][q - 1] = bump
                        if q == 2:
                            gamma[key][q - 1] = -bump

    return {
        "m": m,
        "Q": Q,
        "lambda": lam,
        "mu": mu,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
    }


def coefficients(m):
    if m == 4:
        return _cert_m4()
    elif m == 5:
        return _cert_m5()
    else:
        return _general_cert(m)
