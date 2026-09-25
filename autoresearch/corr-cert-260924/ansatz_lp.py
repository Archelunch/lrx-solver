"""Step 4 deterministic control: certificate ansatz with parameters shared across m.

Every certificate coefficient is an INTEGER combination of shared rational
parameters theta:  coef = sum_k feature_k(q) * monomial_k(vars) * theta_k,
with features = indicators / q-powers at kappa's thresholds and monomials of
degree <= DEG in the family's variables. One LP over theta (and per-m copies of
the certificate tied to theta by equalities) minimises t = max_m epsilon(m)
over the training range. Search side: needs numpy + scipy. Verification is
exact via corrcert.check_certificate (stdlib).

Usage: python3 ansatz_lp.py FAMILY MLO MHI [--deg 2] [--holdout 20] [--cap 0.5]
"""
import json, os, sys, time
from fractions import Fraction
from itertools import combinations_with_replacement
from math import comb, lcm
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, hstack, vstack, block_diag, eye

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corrcert as cc
import search_lp as sl

STEP = ["gt_v", "lt_mu", "eq_d", "eq_md", "ge_md"]
QSTEP = ["qgt_v", "qlt_mu", "qge_md"]
FAMILIES = {   # triple features, triple poly variables
    "F1": (["q", "1"], "abcm"),
    "F2": (["q", "1"] + STEP, "abcm"),
    "F3": (["q", "1"] + STEP, "gaps"),
    "F4": (["q", "1"] + STEP + QSTEP, "abcm"),
    # F5/F6: every role sees the thresholds of all three pairs of its triple
    "F5": (["q", "1"] + [f"gt{x}" for x in "abc"] + [f"lt{x}" for x in "abc"]
           + [f"eq{g}" for g in ("ab", "bc", "ac")] + [f"eqm{g}" for g in ("ab", "bc", "ac")], "abcm"),
    "F6": (["q", "1"] + [f"gt{x}" for x in "abc"] + [f"lt{x}" for x in "abc"]
           + [f"eq{g}" for g in ("ab", "bc", "ac")] + [f"eqm{g}" for g in ("ab", "bc", "ac")]
           + [f"qgt{x}" for x in "abc"] + [f"qlt{x}" for x in "abc"], "abcm"),
}
# F7: F6 features, separate polynomial parameters per unit-gap class ([b-a==1], [c-b==1])
FAMILIES["F7"] = FAMILIES["F6"]
CLASSED = {"F7"}
MU_FEATS = ["q", "1", "eq_a", "eq_m1a", "eq_a1", "eq_ma"]


def feat3(name, m, abc, q):
    """Triple-wide thresholds (F5/F6): gtx = [q > x], ltx = [q < m - x], eqg = [q == gap], eqmg = [q == m - gap]."""
    a, b, c = abc
    X = {"a": a, "b": b, "c": c}
    G = {"ab": b - a, "bc": c - b, "ac": c - a}
    if name.startswith("qgt"):
        return q * (q > X[name[3]])
    if name.startswith("qlt"):
        return q * (q < m - X[name[3]])
    if name.startswith("gt"):
        return int(q > X[name[2]])
    if name.startswith("lt"):
        return int(q < m - X[name[2]])
    if name.startswith("eqm"):
        return int(q == m - G[name[3:]])
    if name.startswith("eq"):
        return int(q == G[name[2:]])
    return {"q": q, "1": 1}[name]


def feat(name, m, u, v, q, abc=None):
    if abc is not None:
        return feat3(name, m, abc, q)
    d = v - u
    return {"q": q, "1": 1, "gt_v": int(q > v), "lt_mu": int(q < m - u), "eq_d": int(q == d),
            "eq_md": int(q == m - d), "ge_md": int(q >= m - d), "qgt_v": q * (q > v),
            "qlt_mu": q * (q < m - u), "qge_md": q * (q >= m - d)}[name]


def mu_feat(name, m, a, q):
    return {"q": q, "1": 1, "eq_a": int(q == a), "eq_m1a": int(q == m - 1 - a),
            "eq_a1": int(q == a + 1), "eq_ma": int(q == m - a)}[name]


def monos(vals, deg):
    out = []
    for d in range(deg + 1):
        for idx in combinations_with_replacement(range(len(vals)), d):
            p = 1
            for i in idx:
                p *= vals[i]
            out.append(p)
    return out


class Ansatz:
    def __init__(self, family, deg=2):
        self.family, self.deg = family, deg
        self.tfeats, self.tvars = FAMILIES[family]
        nt = len(monos([0] * (4 if self.tvars == "abcm" else 3), deg))
        self.ncls = 4 if family in CLASSED else 1
        self.n_cls = 3 * len(self.tfeats) * nt
        self.n_tri = self.ncls * self.n_cls
        self.n_mu = len(MU_FEATS) * len(monos([0, 0], deg))
        self.n_lam = len(monos([0, 0, 0], deg))
        self.n = self.n_tri + self.n_mu + self.n_lam

    def tri_vars(self, m, a, b, c):
        return [a, b, c, m] if self.tvars == "abcm" else [b - a, c - b, m]

    def rows(self, m):
        """For each certificate variable of layout(m) (group order): list of (theta index, int coef)."""
        out = []
        lm = []
        for a, b in cc.pairs(m):
            mo = monos([a, b, m], self.deg)
            out.append([(self.n_tri + self.n_mu + k, c) for k, c in enumerate(mo) if c])
        nm = len(monos([0, 0], self.deg))
        for a in range(m):
            mo = monos([a, m], self.deg)
            for q in range(1, m):
                r = []
                for fi, f in enumerate(MU_FEATS):
                    fv = mu_feat(f, m, a, q)
                    if fv:
                        r += [(self.n_tri + fi * nm + k, fv * c) for k, c in enumerate(mo) if c]
                out.append(r)
        nf = len(self.tfeats)
        for t in cc.triples(m):
            a, b, c = t
            mo = monos(self.tri_vars(m, a, b, c), self.deg)
            nmo = len(mo)
            cls = (2 * (b - a == 1) + (c - b == 1)) * self.n_cls if self.ncls > 1 else 0
            for role, (u, v) in enumerate(((a, b), (b, c), (a, c))):
                for q in range(1, m):
                    r = []
                    for fi, f in enumerate(self.tfeats):
                        fv = feat(f, m, u, v, q, t if self.family in ("F5", "F6", "F7") else None)
                        if fv:
                            base = cls + (role * nf + fi) * nmo
                            r += [(base + k, fv * cm) for k, cm in enumerate(mo) if cm]
                    out.append(r)
        return out

    def cert(self, m, theta):
        """Exact certificate (Q = lcm of theta denominators) from rational theta."""
        L = 1
        for x in theta:
            L = lcm(L, Fraction(x).denominator)
        ti = [int(Fraction(x) * L) for x in theta]
        vec = [sum(ti[k] * c for k, c in r) for r in self.rows(m)]
        return cc.from_vector(m, L, vec)


def keep_rows(m, free):
    """Indices of certificate slots that stay tied to theta (others are free per m)."""
    P, nmu = len(cc.pairs(m)), m * (m - 1)
    pred = next((f[1] for f in free if isinstance(f, tuple)), None)   # ("pred", fn(m, triple) -> free?)
    T = cc.triples(m)
    keep = []
    for i in range(P + nmu + 3 * (m - 1) * comb(m, 3)):
        kind = "lam" if i < P else ("mu" if i < P + nmu else "tri")
        if kind in free:
            continue
        if kind == "tri" and pred and pred(m, T[(i - P - nmu) // (3 * (m - 1))]):
            continue
        keep.append(i)
    return keep


def solve(an, ms, cap=None, l1=False, free=(), margin=0.0, qpow=0):
    """min t s.t. per-m certs valid and epsilon(m) <= t; or, with cap, min ||theta||_1 s.t. eps <= cap."""
    blocksA, blocksB, eqs, nvs = [], [], [], []
    for m in ms:
        A, b = sl.constraints(m)
        # Q(m) = m**qpow: pair rows (6) have RHS Q kappa; triple rows have RHS 0
        sc = np.where(b != 0, float(m) ** qpow, 1.0)
        blocksA.append(A); blocksB.append(b * sc - margin)   # margin: strict slack on every (5),(6) row
        R = an.rows(m)
        r, c, v = [], [], []
        for i, row in enumerate(R):
            for k, cf in row:
                r.append(i); c.append(k); v.append(float(cf))
        T = coo_matrix((v, (r, c)), shape=(len(R), an.n)).tocsr()
        kr = keep_rows(m, free)
        sel = coo_matrix((np.ones(len(kr)), (np.arange(len(kr)), kr)), shape=(len(kr), len(R)))
        eqs.append((sel, T[kr]))
        nvs.append(len(R))
    NX = sum(nvs)
    Ax = block_diag(blocksA, format="csr")
    # epsilon rows: -J_m - m t <= 4 m C(m,3)
    er, ec, ev, eb = [], [], [], []
    off = 0
    for i, m in enumerate(ms):
        P = len(cc.pairs(m))
        for k in range(P + m * (m - 1)):
            er.append(i); ec.append(off + k); ev.append(-1.0 / float(m) ** qpow)
        eb.append(4.0 * m * comb(m, 3))
        off += nvs[i]
    E = coo_matrix((ev, (er, ec)), shape=(len(ms), NX))
    tcol = coo_matrix(np.array([[-float(m)] for m in ms]))
    nth = an.n
    if not l1:
        # vars: theta (nth), x (NX), t
        A_ub = vstack([hstack([coo_matrix((Ax.shape[0], nth)), Ax, coo_matrix((Ax.shape[0], 1))]),
                       hstack([coo_matrix((len(ms), nth)), E, tcol])]).tocsr()
        b_ub = np.concatenate(blocksB + [np.array(eb)])
        S, Th = block_diag([e[0] for e in eqs]), vstack([e[1] for e in eqs])
        A_eq = hstack([-Th, S, coo_matrix((S.shape[0], 1))]).tocsr()
        cost = np.zeros(nth + NX + 1); cost[-1] = 1.0
        res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=np.zeros(S.shape[0]),
                      bounds=(None, None), method=sl.METHOD)
        if res.x is None:
            return None, None, res
        return res.x[:nth], res.x[-1], res
    # L1 on theta: theta = p - n; eps(m) <= cap
    Z = lambda r, c: coo_matrix((r, c))
    A_ub = vstack([hstack([Z(Ax.shape[0], 2 * nth), Ax]),
                   hstack([Z(len(ms), 2 * nth), E])]).tocsr()
    b_ub = np.concatenate(blocksB + [np.array(eb) + cap * np.array(ms, float)])
    S, Th = block_diag([e[0] for e in eqs]), vstack([e[1] for e in eqs])
    A_eq = hstack([-Th, Th, S]).tocsr()
    cost = np.concatenate([np.ones(2 * nth), np.zeros(NX)])
    bounds = [(0, None)] * (2 * nth) + [(None, None)] * NX
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=np.zeros(S.shape[0]), bounds=bounds, method=sl.METHOD)
    if res.x is None:
        return None, None, res
    return res.x[:nth] - res.x[nth:2 * nth], cap, res


MARGIN = 1e-3   # slack reserved on every row so that rounding theta keeps exact feasibility


def rationalise(an, theta, ms, dens=(1, 2, 3, 4, 6, 8, 12, 24, 60, 120, 360, 720, 2520, 10 ** 4, 10 ** 5, 10 ** 6)):
    """First a common grid theta = round(D theta)/D (Q = D), then per-parameter limit_denominator."""
    cands = [("grid", D, [Fraction(round(float(x) * D), D) for x in theta]) for D in dens]
    cands += [("cf", D, [Fraction(float(x)).limit_denominator(D) for x in theta]) for D in dens]
    for kind, D, th in cands:
        ok = True
        for m in ms:
            r = cc.check_certificate(m, an.cert(m, th))
            if not r["proves"]:
                ok = False; break
        if ok:
            return f"{kind}:{D}", th
    return None, None


def forced_tightness(an, theta, m):
    """Max slack (Q=1 float) at the equality order rows; should be ~0 when eps ~ 0."""
    vec = np.array([sum(float(theta[k]) * c for k, c in r) for r in an.rows(m)])
    cert = cc.from_vector(m, 1, vec)
    ps = max(cc.kappa(m, a, b, m - (b - a)) - cc.pair_lhs(cert, a, b, m - (b - a)) for a, b in cc.pairs(m))
    ts = max(-(cert["alpha"][t][m - (t[1] - t[0]) - 1] + cert["beta"][t][m - (t[2] - t[1]) - 1]
               + cert["gamma"][t][m - (t[2] - t[0]) - 1]) for t in cc.triples(m))
    return ps, ts


def main():
    a = sys.argv[1:]
    fam, lo, hi = a[0], int(a[1]), int(a[2])
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    deg, hold, cap = opt("--deg", 2), opt("--holdout", 20), opt("--cap", 0.5)
    an = Ansatz(fam, deg)
    ms = list(range(lo, hi + 1))
    t0 = time.time()
    theta, tstar, res = solve(an, ms)
    rec = {"family": fam, "deg": deg, "train": [lo, hi], "n_params": an.n, "status": res.status,
           "message": res.message, "t_star": tstar, "lp_seconds": round(time.time() - t0, 1)}
    print(json.dumps(rec), flush=True)
    if theta is not None and tstar < 1:
        rec["forced_tightness_max_slack"] = {m: forced_tightness(an, theta, m) for m in (lo, hi)}
        # sparse, slack-tolerant point for rationalisation
        c2 = max(cap, tstar + 0.05) if tstar < 0.9 else tstar
        th2, _, r2 = solve(an, ms, cap=min(c2, 0.95), l1=True, margin=MARGIN)
        rec["l1_status"] = r2.status
        rec["l1_nonzero"] = int(sum(abs(x) > 1e-9 for x in th2)) if th2 is not None else None
        D, thr = rationalise(an, th2, ms) if th2 is not None else (None, None)
        if D is None:
            D, thr = rationalise(an, theta, ms)
        rec["rational_D"] = D
        if thr is not None:
            rec["theta"] = [str(x) for x in thr]
            rec["train_eps"] = {m: str(cc.check_certificate(m, an.cert(m, thr))["epsilon"]) for m in ms}
            hres = {}
            for m in range(hi + 1, hold + 1):
                ce = an.cert(m, thr)
                r = cc.check_certificate(m, ce, max_violations=3)
                r["Q"] = ce["Q"]
                hres[m] = {"ok": r["ok"], "epsilon": str(r["epsilon"]), "proves": r["proves"],
                           "n_viol": r["n_violations"],
                           "first": [v[:6] + (str(Fraction(v[6], r["Q"] if "Q" in r else 1)),) for v in r["violations"][:3]]}
                print(f"  holdout m={m}: proves={r['proves']} eps={float(r['epsilon']):.4g} nviol={r['n_violations']} "
                      f"first={hres[m]['first'][:1]}", flush=True)
                if not r["proves"]:
                    break
            rec["holdout"] = hres
    rec["total_seconds"] = round(time.time() - t0, 1)
    os.makedirs(os.path.join(HERE, "ansatz"), exist_ok=True)
    with open(os.path.join(HERE, "ansatz", f"{fam}-d{deg}-m{lo}-{hi}.json"), "w") as fh:
        json.dump(rec, fh, indent=1, default=str)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("theta", "holdout")}, default=str), flush=True)


if __name__ == "__main__":
    main()
