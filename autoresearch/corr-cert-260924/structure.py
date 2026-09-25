"""Structure hunt (search side; scipy). Supports: restricting triple support,
L-infinity gauge, exact vertex recovery, tight-row listing.
Usage: python3 structure.py support M1 M2 ...    # LP epsilon under triple-support restrictions
"""
import sys, time, json, os
from fractions import Fraction
from math import comb, lcm
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, hstack, vstack
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corrcert as cc
import search_lp as sl

SUPPORTS = {
    "all": lambda t: True,
    "unit-gap (b-a=1 or c-b=1)": lambda t: t[1] - t[0] == 1 or t[2] - t[1] == 1,
    "consecutive (b-a=1 and c-b=1)": lambda t: t[1] - t[0] == 1 and t[2] - t[1] == 1,
    "b-a=1 only": lambda t: t[1] - t[0] == 1,
    "c-b=1 only": lambda t: t[2] - t[1] == 1,
    "none": lambda t: False,
}
BA1 = lambda t: t[1] - t[0] == 1
ROLE_SUPPORTS = {
    "b-a=1, alpha=0": lambda t, r: BA1(t) and r != 0,
    "b-a=1, beta=0": lambda t, r: BA1(t) and r != 1,
    "b-a=1, gamma=0": lambda t, r: BA1(t) and r != 2,
    "b-a=1, alpha only": lambda t, r: BA1(t) and r == 0,
    "b-a=1, beta only": lambda t, r: BA1(t) and r == 1,
    "b-a=1, gamma only": lambda t, r: BA1(t) and r == 2,
}


def bounds_for(m, support, box=None):
    P, T, nv, lam, mu, tri, base_t = sl.layout(m)
    b = [(None, None) if box is None else (-box, box)] * nv
    for t in T:
        for role in range(3):
            ok = support(t, role) if support.__code__.co_argcount == 2 else support(t)
            if not ok:
                for q in range(1, m):
                    b[tri(t, role, q)] = (0, 0)
    return b


def min_eps(m, support):
    A, bb = sl.constraints(m)
    j = sl.j_vector(m)
    r = linprog(-j, A_ub=A, b_ub=bb, bounds=bounds_for(m, support), method=sl.METHOD)
    if r.x is None:
        return None, r
    return -float(j @ r.x) / m - 4 * comb(m, 3), r


def main_support(ms, which=None):
    for m in ms:
        for name, fn in (which or SUPPORTS).items():
            t0 = time.time()
            e, r = min_eps(m, fn)
            print(json.dumps({"m": m, "support": name, "lp_eps": e, "status": r.status,
                              "s": round(time.time() - t0, 2)}), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "support":
        main_support([int(x) for x in sys.argv[2:]])
    if sys.argv[1] == "roles":
        main_support([int(x) for x in sys.argv[2:]], ROLE_SUPPORTS)
    if sys.argv[1] == "ba1":
        main_support([int(x) for x in sys.argv[2:]], {"b-a=1 only": SUPPORTS["b-a=1 only"]})


# ---------------- clean gauge: min L-infinity, then min L1 at that bound ----------------
def gauge_solve(m, support, method=None):
    A, bb = sl.constraints(m)
    j = sl.j_vector(m)
    nv = A.shape[1]
    zero = [lo == 0 and hi == 0 for lo, hi in bounds_for(m, support)]
    free = [i for i in range(nv) if not zero[i]]
    A = A[:, free]; jf = j[free]; n = len(free)
    jrow = coo_matrix(-jf[None, :])
    epsb = 4.0 * m * comb(m, 3)          # -J <= 4 m C(m,3)  <=>  epsilon <= 0
    meth = method or sl.METHOD
    # stage 1: variables x (n), M; |x_i| <= M
    I = coo_matrix((np.ones(n), (range(n), range(n))), shape=(n, n))
    one = coo_matrix(-np.ones((n, 1)))
    A1 = vstack([hstack([A, coo_matrix((A.shape[0], 1))]), hstack([jrow, coo_matrix((1, 1))]),
                 hstack([I, one]), hstack([-I, one])]).tocsr()
    b1 = np.concatenate([bb, [epsb], np.zeros(2 * n)])
    c1 = np.zeros(n + 1); c1[-1] = 1
    r1 = linprog(c1, A_ub=A1, b_ub=b1, bounds=(None, None), method=meth)
    Mstar = r1.x[-1]
    # stage 2: min L1 with |x_i| <= Mstar (x = p - q)
    A2 = vstack([hstack([A, -A]), hstack([jrow, -jrow])]).tocsr()
    b2 = np.concatenate([bb, [epsb]])
    r2 = linprog(np.ones(2 * n), A_ub=A2, b_ub=b2, bounds=[(0, Mstar * (1 + 1e-9))] * (2 * n), method=meth)
    x = np.zeros(nv)
    xs = r2.x[:n] - r2.x[n:] if r2.x is not None else r1.x[:n]
    x[free] = xs
    return x, Mstar, r1, r2


def exact_vertex(m, x, dens=(1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 36, 48, 60, 120, 240, 360, 720, 2520,
                             5040, 10 ** 4, 10 ** 5, 10 ** 6)):
    for D in dens:
        fr = [Fraction(float(v)).limit_denominator(D) for v in x]
        L = 1
        for f in fr:
            L = lcm(L, f.denominator)
        cert = cc.from_vector(m, L, [int(f * L) for f in fr])
        r = cc.check_certificate(m, cert)
        if r["ok"] and r["epsilon"] == 0:
            return D, L, cert
    return None, None, None


# ---------------- exact recovery from the float active set ----------------
def exact_active_set(m, x, support, tol=1e-6, free_den=12, prefix_den=None):
    """Solve the tight rows of (5),(6) and epsilon=0 exactly (Fractions); free columns
    take small-denominator roundings of x. Returns an exact cert (or None) after full check."""
    A, bb = sl.constraints(m)
    A = A.tocsr()
    nv = A.shape[1]
    zero = {i for i, (lo, hi) in enumerate(bounds_for(m, support)) if lo == 0 and hi == 0}
    fixed = {i: Fraction(0) for i in zero}
    if prefix_den:
        for i in range(nv):
            if i not in zero:
                f = Fraction(float(x[i])).limit_denominator(prefix_den)
                if abs(float(f) - x[i]) < 1e-9:
                    fixed[i] = f
    zero = set(fixed)
    slack = bb - A @ x
    rows = []
    for i in np.nonzero(slack <= tol * (1 + np.abs(bb)))[0]:
        s, e = A.indptr[i], A.indptr[i + 1]
        rows.append(({int(c): Fraction(int(round(v))) for c, v in zip(A.indices[s:e], A.data[s:e]) if int(c) not in zero},
                     Fraction(int(round(bb[i]))) - sum(Fraction(int(round(v))) * fixed[int(c)]
                                                       for c, v in zip(A.indices[s:e], A.data[s:e]) if int(c) in zero)))
    j = sl.j_vector(m)
    rows.append(({i: Fraction(-1) for i in range(nv) if j[i] and i not in zero},
                 Fraction(4 * m * comb(m, 3)) + sum(fixed[i] for i in zero if j[i])))
    # sparse Gauss-Jordan
    piv = {}          # col -> (row dict, rhs) with coefficient 1 at col
    for r, b in rows:
        r = dict(r)
        for c in [c for c in r if c in piv]:
            pass
        changed = True
        while changed:
            changed = False
            for c in list(r):
                if c in piv and r.get(c):
                    f = r[c]; pr, pb = piv[c]
                    for k, v in pr.items():
                        nvv = r.get(k, 0) - f * v
                        if nvv:
                            r[k] = nvv
                        else:
                            r.pop(k, None)
                    b -= f * pb
                    changed = True
        r = {k: v for k, v in r.items() if v}
        if not r:
            if b != 0:
                return None, "inconsistent tight system"
            continue
        c0 = max(r, key=lambda k: abs(r[k]))
        f = r[c0]
        r = {k: v / f for k, v in r.items()}; b = b / f
        # eliminate c0 from existing pivots
        for c, (pr, pb) in list(piv.items()):
            if c0 in pr:
                g = pr[c0]
                for k, v in r.items():
                    nvv = pr.get(k, 0) - g * v
                    if nvv:
                        pr[k] = nvv
                    else:
                        pr.pop(k, None)
                piv[c] = (pr, pb - g * b)
        piv[c0] = (r, b)
    val = {}
    for i in range(nv):
        if i in zero:
            val[i] = fixed[i]
        elif i not in piv:
            val[i] = Fraction(float(x[i])).limit_denominator(free_den)
    for c, (pr, pb) in piv.items():
        val[c] = pb - sum(v * val[k] for k, v in pr.items() if k != c)
    fr = [val[i] for i in range(nv)]
    L = 1
    for f in fr:
        L = lcm(L, f.denominator)
    cert = cc.from_vector(m, L, [int(f * L) for f in fr])
    r = cc.check_certificate(m, cert)
    return (cert if r["ok"] and r["epsilon"] == 0 else None), {"Q": L, "ok": r["ok"], "eps": str(r["epsilon"]),
                                                               "nviol": r["n_violations"], "n_free": nv - len(piv) - len(zero),
                                                               "n_tight": len(rows) - 1}


def small_q_scan(m, support, qmax=None):
    """For Q = 1..qmax: round Q*x (x from two LP points) to integers, group repair, exact check.
    Returns list of (Q, base, epsilon) for certs that prove (epsilon < 1)."""
    e, r = min_eps(m, support)
    xg, M, _, _ = gauge_solve(m, support, "highs-ds")
    out = []
    for Q in range(1, (qmax or 2 * m) + 1):
        best = None
        for base, x in (("plain", r.x), ("gauge", xg)):
            cert = cc.from_vector(m, Q, [int(round(v * Q)) for v in x])
            cc.repair(cert)
            chk = cc.check_certificate(m, cert)
            if chk["proves"] and (best is None or chk["epsilon"] < best[2]):
                best = (Q, base, chk["epsilon"], cert)
        if best:
            out.append(best)
    return out
