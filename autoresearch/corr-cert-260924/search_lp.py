"""LP regeneration of Theorem 3 certificates (SEARCH SIDE ONLY: needs numpy+scipy).

Families written under this directory:
  certs/m<m>.json        max J (min epsilon), Q=1 LP -> round to Q=1e6 -> repair -> exact check
  certs-canon/m<m>.json  epsilon <= plain rounded epsilon, min L1 norm of all coefficients
  certs-sym/m<m>.json    as canon, plus reversal symmetry a -> m-1-a imposed
  certs-exact/m<m>.json  (--families exact) L1-min LP with epsilon <= 0 (sym, then plain
                         constraints), rationalised by limit_denominator; written only if
                         the exact checker returns epsilon == 0 (Q = lcm of denominators)
Raw float LP vectors go to lp-raw/<family>-m<m>.json (for PATTERNS.md).
Usage: python3 search_lp.py M1 M2 ... [--families plain,canon,sym]
"""
import json, os, sys, time
from fractions import Fraction
from math import comb
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, hstack, vstack

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corrcert as cc

Q = 10 ** 6
METHOD = os.environ.get("CORRCERT_LP_METHOD", "highs-ipm")  # highs-ipm with crossover; "highs" was 6x slower at m=12


def layout(m):
    n, P = m - 1, cc.pairs(m)
    T = cc.triples(m)
    pidx = {pr: i for i, pr in enumerate(P)}
    tidx = {t: i for i, t in enumerate(T)}
    base_mu, base_t = len(P), len(P) + m * n
    nv = base_t + 3 * n * len(T)
    lam = lambda a, b: pidx[(a, b)]
    mu = lambda a, q: base_mu + a * n + q - 1
    tri = lambda t, role, q: base_t + tidx[t] * 3 * n + role * n + q - 1   # role 0,1,2 = alpha,beta,gamma
    return P, T, nv, lam, mu, tri, base_t


def constraints(m):
    """A_ub x <= b_ub for (5), (6) with Q = 1."""
    P, T, nv, lam, mu, tri, _ = layout(m)
    r, c, v, b = [], [], [], []
    row = 0
    for t in T:
        for q in range(1, m):
            for s in range(1, m):
                if q + s == m:
                    continue
                for role, qq in ((0, q), (1, s), (2, (q + s) % m)):
                    r.append(row); c.append(tri(t, role, qq)); v.append(1.0)
                b.append(0.0); row += 1
    for a, bb in P:
        for q in range(1, m):
            r += [row, row, row]; c += [lam(a, bb), mu(a, q), mu(bb, m - q)]; v += [1.0, 1.0, 1.0]
            for x in range(bb + 1, m):
                r.append(row); c.append(tri((a, bb, x), 0, q)); v.append(-1.0)
            for x in range(a):
                r.append(row); c.append(tri((x, a, bb), 1, q)); v.append(-1.0)
            for x in range(a + 1, bb):
                r.append(row); c.append(tri((a, x, bb), 2, q)); v.append(-1.0)
            b.append(float(cc.kappa(m, a, bb, q))); row += 1
    A = coo_matrix((v, (r, c)), shape=(row, nv)).tocsr()
    return A, np.array(b)


def j_vector(m):
    P, T, nv, lam, mu, tri, base_t = layout(m)
    j = np.zeros(nv); j[:base_t] = 1.0
    return j


# ---------- reversal symmetry sigma: a -> m-1-a ----------
def sym_shift(m, a, b):
    """d_ab = kappa_{sigma(a,b)}(q) - kappa_ab(q); must not depend on q."""
    s = (m - 1 - b, m - 1 - a)
    ds = {cc.kappa(m, *s, q) - cc.kappa(m, a, b, q) for q in range(1, m)}
    assert len(ds) == 1, (m, a, b, ds)
    return ds.pop()


def sym_image(cert):
    """Image of an exact cert under sigma (lambda shifted by Q*d)."""
    m, Qc = cert["m"], cert["Q"]
    img = {"m": m, "Q": Qc, "lambda": {}, "mu": {}, "alpha": {}, "beta": {}, "gamma": {}}
    for a, b in cc.pairs(m):
        img["lambda"][(m - 1 - b, m - 1 - a)] = cert["lambda"][(a, b)] + Qc * sym_shift(m, a, b)
    for a in range(m):
        img["mu"][m - 1 - a] = [cert["mu"][a][m - q - 1] for q in range(1, m)]
    for t in cc.triples(m):
        a, b, c = t
        s = (m - 1 - c, m - 1 - b, m - 1 - a)
        img["alpha"][s], img["beta"][s], img["gamma"][s] = cert["beta"][t][:], cert["alpha"][t][:], cert["gamma"][t][:]
    return img


def sym_equalities(m):
    P, T, nv, lam, mu, tri, _ = layout(m)
    r, c, v, b = [], [], [], []
    row = 0
    def eq(i, j, rhs):
        nonlocal row
        if i == j and rhs == 0:
            return
        r.extend([row, row]); c.extend([i, j]); v.extend([1.0, -1.0]); b.append(rhs); row += 1
    for a, bb in P:
        eq(lam(m - 1 - bb, m - 1 - a), lam(a, bb), float(sym_shift(m, a, bb)))
    for a in range(m):
        for q in range(1, m):
            eq(mu(m - 1 - a, q), mu(a, m - q), 0.0)
    for t in T:
        s = (m - 1 - t[2], m - 1 - t[1], m - 1 - t[0])
        for q in range(1, m):
            eq(tri(s, 0, q), tri(t, 1, q), 0.0)
            eq(tri(s, 1, q), tri(t, 0, q), 0.0)
            eq(tri(s, 2, q), tri(t, 2, q), 0.0)
    return coo_matrix((v, (r, c)), shape=(row, nv)).tocsr(), np.array(b)


def symmetry_precheck(m):
    """(i) E invariant under the induced map on orders (m <= 7 all orders);
    (ii) kappa shift constant in q (asserted in sym_shift); sum of shifts = 0."""
    from itertools import permutations
    if m <= 7:
        for p in permutations(range(m)):
            z = cc.positions(p)
            z2 = [0] * m
            for a in range(m):
                z2[m - 1 - a] = (-z[a]) % m
            p2 = [0] * m
            for a in range(m):
                p2[z2[a]] = a
            assert cc.stats(p)["E"] == cc.stats(p2)["E"]
    return sum(sym_shift(m, a, b) for a, b in cc.pairs(m)) == 0


# ---------- solve ----------
def solve(m, family, eps_cap=None):
    A, b = constraints(m)
    nv = A.shape[1]
    j = j_vector(m)
    kw = dict(method=METHOD, options={"presolve": True})
    A_eq = b_eq = None
    if family == "sym":
        A_eq, b_eq = sym_equalities(m)
    if family == "plain":
        res = linprog(-j, A_ub=A, b_ub=b, A_eq=A_eq, b_eq=b_eq, bounds=(None, None), **kw)
        x = res.x
    else:
        # x = xp - xn; J >= m(-4C(m,3) - eps_cap)
        jmin = m * (-4 * comb(m, 3) - float(eps_cap))
        A2 = hstack([A, -A])
        A2 = vstack([A2, hstack([coo_matrix(-j[None, :]), coo_matrix(j[None, :])])])
        b2 = np.append(b, -jmin)
        Aeq2 = hstack([A_eq, -A_eq]) if A_eq is not None else None
        res = linprog(np.ones(2 * nv), A_ub=A2, b_ub=b2, A_eq=Aeq2, b_eq=b_eq, bounds=(0, None), **kw)
        x = res.x[:nv] - res.x[nv:] if res.x is not None else None
    if x is None:
        raise RuntimeError(f"LP failed m={m} {family}: {res.message}")
    eps_lp = -float(j @ x) / m - 4 * comb(m, 3)
    return x, eps_lp, res


def round_repair_check(m, x):
    cert = cc.from_vector(m, Q, [int(round(v * Q)) for v in x])
    cc.repair(cert)
    return cert, cc.check_certificate(m, cert)


def exact_family(m):
    """Try to rationalise an L1-minimal epsilon <= 0 LP vertex into an exact epsilon = 0 cert."""
    from math import lcm
    for fam in ("sym", "canon"):
        x, eps_lp, res = solve(m, fam, 0.0)
        for D in (1, 2, 3, 4, 6, 12, 24, 60, 120, 360, 1000, 5000):
            fr = [Fraction(v).limit_denominator(D) for v in x]
            L = 1
            for f in fr:
                L = lcm(L, f.denominator)
            cert = cc.from_vector(m, L, [int(f * L) for f in fr])
            chk = cc.check_certificate(m, cert)
            if chk["ok"] and chk["epsilon"] == 0:
                return fam, D, cert, chk, x
    return None


def main():
    args = sys.argv[1:]
    fams = ["plain", "canon", "sym"]
    if "--families" in args:
        i = args.index("--families"); fams = args[i + 1].split(","); del args[i:i + 2]
    ms = [int(a) for a in args] or list(range(4, 13))
    for d in ("certs", "certs-canon", "certs-sym", "lp-raw"):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    logp = os.path.join(HERE, "search_log.jsonl")
    for m in ms:
        plain_eps = None
        pf = os.path.join(HERE, "certs", f"m{m}.json")
        if os.path.exists(pf):
            plain_eps = Fraction(json.load(open(pf))["epsilon"])
        for fam in fams:
            t0 = time.time()
            if fam == "exact":
                os.makedirs(os.path.join(HERE, "certs-exact"), exist_ok=True)
                got = exact_family(m)
                rec = {"m": m, "family": "exact", "found": got is not None,
                       "total_seconds": round(time.time() - t0, 2)}
                if got:
                    base, D, cert, chk, x = got
                    rec.update({"base": base, "limit_denominator": D, "Q": cert["Q"], "epsilon": "0",
                                "checks": chk["checks"], "sym_exact": sym_image(cert) == cert})
                    with open(os.path.join(HERE, "certs-exact", f"m{m}.json"), "w") as fh:
                        json.dump(cc.to_json(cert, {"epsilon": "0", "family": "exact", "base": base}), fh)
                with open(logp, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                print(f"m={m:2d} exact {rec}", flush=True)
                continue
            rec = {"m": m, "family": fam}
            if fam == "sym":
                rec["sym_precheck"] = symmetry_precheck(m)
            cap = None if fam == "plain" else plain_eps
            if fam != "plain" and cap is None:
                print(f"m={m} {fam}: skipped (no plain cert)"); continue
            x, eps_lp, res = solve(m, fam, cap)
            t_lp = time.time() - t0
            cert, chk = round_repair_check(m, x)
            rec.update({"lp_status": res.status, "lp_epsilon": eps_lp, "eps_cap": str(cap) if cap is not None else None,
                        "l1_Q1": float(np.abs(x).sum()), "ok": chk["ok"], "epsilon": str(chk["epsilon"]),
                        "epsilon_float": float(chk["epsilon"]), "proves": chk["proves"],
                        "checks": chk["checks"], "expected_checks": cc.expected_checks(m),
                        "n_violations": chk["n_violations"], "lp_seconds": round(t_lp, 2),
                        "total_seconds": round(time.time() - t0, 2)})
            if fam == "sym":
                img = sym_image(cert)
                rec["rounded_cert_exactly_symmetric"] = img == cert
                rec["sym_image_check_ok"] = cc.check_certificate(m, img)["ok"]
            if fam == "plain":
                img = sym_image(cert)
                ic = cc.check_certificate(m, img)
                rec["sym_image_of_plain_ok"] = ic["ok"] and ic["epsilon"] == chk["epsilon"]
            if chk["ok"]:
                sub = {"plain": "certs", "canon": "certs-canon", "sym": "certs-sym"}[fam]
                with open(os.path.join(HERE, sub, f"m{m}.json"), "w") as fh:
                    json.dump(cc.to_json(cert, {"epsilon": str(chk["epsilon"]), "family": fam,
                                                "lp_epsilon": eps_lp}), fh)
                if fam == "plain":
                    plain_eps = chk["epsilon"]
            with open(os.path.join(HERE, "lp-raw", f"{fam}-m{m}.json"), "w") as fh:
                json.dump({"m": m, "family": fam, "x": [float(v) for v in x]}, fh)
            with open(logp, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(f"m={m:2d} {fam:5s} lp_eps={eps_lp:.3e} eps={chk['epsilon']} (~{float(chk['epsilon']):.3e}) "
                  f"ok={chk['ok']} proves={chk['proves']} checks={chk['checks']} "
                  f"lp={t_lp:.1f}s tot={rec['total_seconds']}s"
                  + (f" symprecheck={rec.get('sym_precheck')} exact_sym={rec.get('rounded_cert_exactly_symmetric')}" if fam == "sym" else "")
                  + (f" sym_image_ok={rec['sym_image_of_plain_ok']}" if fam == "plain" else ""), flush=True)


if __name__ == "__main__":
    main()
