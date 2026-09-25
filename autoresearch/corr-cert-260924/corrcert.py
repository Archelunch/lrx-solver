"""Exact (stdlib) evaluator for the correlation certificate of THEOREM.md.

All arithmetic is on Python ints and Fractions. Certificates are plain dicts:
  {"m": m, "Q": Q,
   "lambda": {(a, b): int},                      a < b
   "mu":     {a: [mu_a(1), ..., mu_a(m-1)]},
   "alpha" / "beta" / "gamma": {(a, b, c): [v(1), ..., v(m-1)]}}   a < b < c
JSON order (the group's array order): lambda pairs lexicographic; mu by a then
q; triples lexicographic, each triple alpha(1..m-1), beta(1..m-1), gamma(1..m-1).
"""
from fractions import Fraction
from itertools import combinations
from math import comb


# ---------- statistics from the definitions ----------
def stats(p):
    """C, K, H, V, E = C - 4K - 2H of a circular order p (a permutation of 0..m-1)."""
    m = len(p)
    U = [2 * sum(1 for j in range(1, m) if p[(s + j) % m] < j) - m + 1 for s in range(m)]
    w = [2 * x - m + 1 for x in p]
    C = sum(w[s] * U[s] for s in range(m))
    V = sum(x * x for x in U)
    H = sum(1 for i, j in combinations(range(m), 2) if (p[i] - i - p[j] + j) % m == 0)
    K = sum(1 for i, j, k in combinations(range(m), 3)
            if (p[j] - p[i]) % m < (p[k] - p[i]) % m)
    return {"C": C, "K": K, "H": H, "V": V, "E": C - 4 * K - 2 * H}


def positions(p):
    z = [0] * len(p)
    for i, a in enumerate(p):
        z[a] = i
    return z


def q_of(z, a, b):
    return (z[b] - z[a]) % len(z)


def f_ab(m, a, b, q):
    return 2 * (2 * a - m + 1) * (q > b) + 2 * (2 * b - m + 1) * (q < m - a)


def kappa(m, a, b, q):
    return -m * f_ab(m, a, b, q) - 4 * (m - 2 * (b - a)) * q + 2 * m * (q == b - a)


def pairs(m):
    return list(combinations(range(m), 2))


def triples(m):
    return list(combinations(range(m), 3))


# ---------- certificate (de)serialisation ----------
def to_json(cert, extra=None):
    m = cert["m"]
    out = {"m": m, "Q": cert["Q"],
           "lambda": [cert["lambda"][pr] for pr in pairs(m)],
           "mu": [v for a in range(m) for v in cert["mu"][a]],
           "triples": [v for t in triples(m)
                       for v in cert["alpha"][t] + cert["beta"][t] + cert["gamma"][t]]}
    out.update(extra or {})
    return out


def from_json(d):
    m, n = d["m"], d["m"] - 1
    tri = d["triples"]
    cert = {"m": m, "Q": d["Q"],
            "lambda": dict(zip(pairs(m), d["lambda"])),
            "mu": {a: list(d["mu"][a * n:(a + 1) * n]) for a in range(m)},
            "alpha": {}, "beta": {}, "gamma": {}}
    for i, t in enumerate(triples(m)):
        blk = tri[3 * n * i:3 * n * (i + 1)]
        cert["alpha"][t], cert["beta"][t], cert["gamma"][t] = blk[:n], blk[n:2 * n], blk[2 * n:]
    return cert


def from_vector(m, Q, x):
    """Vector in the group's array order -> cert dict."""
    P, n = len(pairs(m)), m - 1
    return from_json({"m": m, "Q": Q, "lambda": list(x[:P]),
                      "mu": list(x[P:P + m * n]), "triples": list(x[P + m * n:])})


# ---------- exact check of (5), (6), (7) ----------
def pair_lhs(cert, a, b, q):
    """P_ab(q) of (6)."""
    m = cert["m"]
    s = cert["lambda"][(a, b)] + cert["mu"][a][q - 1] + cert["mu"][b][m - q - 1]
    s -= sum(cert["alpha"][(a, b, c)][q - 1] for c in range(b + 1, m))
    s -= sum(cert["beta"][(c, a, b)][q - 1] for c in range(a))
    s -= sum(cert["gamma"][(a, c, b)][q - 1] for c in range(a + 1, b))
    return s


def epsilon(cert):
    m, Q = cert["m"], cert["Q"]
    J = sum(cert["lambda"].values()) + sum(sum(v) for v in cert["mu"].values())
    return Fraction(-J, Q * m) - 4 * comb(m, 3)


def _well_formed(m, cert):
    n = m - 1
    if cert.get("m") != m or not isinstance(cert.get("Q"), int) or cert["Q"] <= 0:
        return "bad m or Q"
    if set(cert["lambda"]) != set(pairs(m)) or set(cert["mu"]) != set(range(m)):
        return "bad index sets"
    vals = list(cert["lambda"].values())
    for a in range(m):
        if len(cert["mu"][a]) != n:
            return "bad mu length"
        vals += cert["mu"][a]
    for key in ("alpha", "beta", "gamma"):
        if set(cert[key]) != set(triples(m)):
            return "bad triple index set"
        for v in cert[key].values():
            if len(v) != n:
                return "bad triple length"
            vals += v
    if not all(type(v) is int for v in vals):
        return "non-integer coefficient"
    return None


def check_certificate(m, cert, max_violations=10):
    """Verify (5) and (6) exactly and compute epsilon (7).

    Returns {"ok", "epsilon" (Fraction), "proves" (epsilon < 1), "checks",
    "violations": [(kind, a, b, c, q, t, slack)]} with slack < 0 for violations.
    """
    bad = _well_formed(m, cert)
    if bad:
        return {"ok": False, "epsilon": None, "proves": False, "checks": 0,
                "violations": [("malformed", bad)]}
    checks, nviol, viol = 0, 0, []
    for t in triples(m):
        al, be, ga = cert["alpha"][t], cert["beta"][t], cert["gamma"][t]
        for q in range(1, m):
            for s in range(1, m):
                if q + s == m:
                    continue
                checks += 1
                slack = -(al[q - 1] + be[s - 1] + ga[(q + s) % m - 1])
                if slack < 0:
                    nviol += 1
                    viol.append(("triple5", t[0], t[1], t[2], q, s, slack))
    Q = cert["Q"]
    for a, b in pairs(m):
        for q in range(1, m):
            checks += 1
            slack = Q * kappa(m, a, b, q) - pair_lhs(cert, a, b, q)
            if slack < 0:
                nviol += 1
                viol.append(("pair6", a, b, None, q, None, slack))
    shown = viol[:max_violations]
    eps = epsilon(cert)
    return {"ok": nviol == 0, "epsilon": eps, "proves": nviol == 0 and eps < 1,
            "checks": checks, "n_violations": nviol, "violations": shown}


def expected_checks(m):
    return comb(m, 3) * (m - 1) * (m - 2) + comb(m, 2) * (m - 1)


# ---------- repair (the group's procedure) ----------
def repair(cert):
    """Per triple subtract max positive (5) violation from all alpha(q);
    then per pair subtract max positive (6) violation from lambda_ab. In place."""
    m, Q = cert["m"], cert["Q"]
    for t in triples(m):
        al, be, ga = cert["alpha"][t], cert["beta"][t], cert["gamma"][t]
        v = max(al[q - 1] + be[s - 1] + ga[(q + s) % m - 1]
                for q in range(1, m) for s in range(1, m) if q + s != m)
        if v > 0:
            cert["alpha"][t] = [x - v for x in al]
    for a, b in pairs(m):
        v = max(pair_lhs(cert, a, b, q) - Q * kappa(m, a, b, q) for q in range(1, m))
        if v > 0:
            cert["lambda"][(a, b)] -= v
    return cert


# ---------- negative controls ----------
def negative_controls(m, cert):
    """Corrupt single coefficients of a valid cert just past their tightest slack.
    Returns list of (description, rejected: bool)."""
    import copy
    out = []
    t = triples(m)[0]
    al, be, ga = cert["alpha"][t], cert["beta"][t], cert["gamma"][t]
    sl = min(-(al[0] + be[s - 1] + ga[(1 + s) % m - 1]) for s in range(1, m) if 1 + s != m)
    c = copy.deepcopy(cert)
    c["alpha"][t][0] += sl + 1
    out.append((f"alpha{t}(1) += {sl + 1}", not check_certificate(m, c)["ok"]))
    Q, pr = cert["Q"], pairs(m)[-1]
    sl = min(Q * kappa(m, *pr, q) - pair_lhs(cert, *pr, q) for q in range(1, m))
    c = copy.deepcopy(cert)
    c["lambda"][pr] += sl + 1
    out.append((f"lambda{pr} += {sl + 1}", not check_certificate(m, c)["ok"]))
    sl = min(Q * kappa(m, 0, b, q) - pair_lhs(cert, 0, b, q)
             for b in range(1, m) for q in [1])
    c = copy.deepcopy(cert)
    c["mu"][0][0] += sl + 1
    out.append((f"mu_0(1) += {sl + 1}", not check_certificate(m, c)["ok"]))
    c = copy.deepcopy(cert)
    c["mu"][0][0] = float(c["mu"][0][0])
    out.append(("float coefficient", not check_certificate(m, c)["ok"]))
    return out
