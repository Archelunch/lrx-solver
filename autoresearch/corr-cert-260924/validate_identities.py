"""Brute-force validation of Lemma 2, identity (4), property (3) and C <= 4K + 2H.

Full enumeration for m = 4..8 (all m! orders); seeded sample of 20000 for m = 9, 10.
Usage: python3 validate_identities.py [--out validate.json]
"""
import json, random, sys, time
from collections import Counter
from fractions import Fraction
from itertools import permutations
from math import comb
sys.path.insert(0, __import__("os").path.dirname(__file__))
from corrcert import stats, positions, q_of, f_ab, kappa, pairs, triples


def check_perm(p):
    """Return (stats, list of failed identity names)."""
    m = len(p)
    st = stats(p)
    z = positions(p)
    q = {(a, b): q_of(z, a, b) for a, b in pairs(m)}
    fails = []
    if st["C"] != sum(f_ab(m, a, b, v) for (a, b), v in q.items()):
        fails.append("lemma2_C")
    if st["H"] != sum(v == b - a for (a, b), v in q.items()):
        fails.append("lemma2_H")
    if Fraction(st["K"]) != comb(m, 3) - Fraction(sum((m - 2 * (b - a)) * v for (a, b), v in q.items()), m):
        fails.append("lemma2_K")
    if m * st["E"] != -sum(kappa(m, a, b, v) for (a, b), v in q.items()) - 4 * m * comb(m, 3):
        fails.append("identity4")
    for a in range(m):
        if sorted((z[b] - z[a]) % m for b in range(m) if b != a) != list(range(1, m)):
            fails.append("q_bijection"); break
    for a, b, c in triples(m):
        if q[(a, c)] != (q[(a, b)] + q[(b, c)]) % m or q[(a, b)] + q[(b, c)] == m:
            fails.append("property3"); break
    if st["E"] > 0:
        fails.append("C<=4K+2H")
    return st, fails


def run(m, perms, label):
    t0 = time.time()
    fail_count, dist, n, first_fail = Counter(), Counter(), 0, None
    best, best_perms = None, []
    for p in perms:
        n += 1
        st, fails = check_perm(p)
        for f in fails:
            fail_count[f] += 1
        if fails and first_fail is None:
            first_fail = (list(p), fails)
        e = st["E"]
        dist[e] += 1
        if best is None or e > best:
            best, best_perms = e, []
        if e == best and p[0] == 0 and len(best_perms) < 12:
            best_perms.append(list(p))
    return {"m": m, "mode": label, "n": n, "fails": dict(fail_count), "first_fail": first_fail,
            "max_E": best, "count_at_max": dist[best],
            "examples_at_max_p0=0": best_perms,
            "E_distribution": {str(k): v for k, v in sorted(dist.items(), reverse=True)},
            "seconds": round(time.time() - t0, 2)}


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    res = []
    for m in range(4, 9):
        res.append(run(m, permutations(range(m)), "all"))
    rng = random.Random(260924)
    for m in (9, 10):
        def sample(m=m):
            for _ in range(20000):
                p = list(range(m)); rng.shuffle(p); yield p
        res.append(run(m, sample(), "sample20000_seed260924"))
    ok = True
    for r in res:
        top = list(r["E_distribution"].items())[:4]
        print(f"m={r['m']:2d} {r['mode']:>22s} n={r['n']:6d} fails={r['fails'] or 'none'} "
              f"maxE={r['max_E']} #atmax={r['count_at_max']} top={top} {r['seconds']}s")
        if r["fails"]:
            ok = False
            print("  FIRST FAILURE:", r["first_fail"])
    print("ALL IDENTITIES HOLD" if ok else "!!! IDENTITY FAILURE: definitions wrong, do not proceed")
    if out:
        with open(out, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
