"""Symmetry tests, independent cross-checks and literal sorting words for C(9,r).

Usage: python check_class.py r [--symmetry-sample N]
Reads class_m9_r{r}_full.json (or _sample.json) and the class bitmap written by
enumerate_class.py; writes check_m9_r{r}.json.
"""
import argparse, hashlib, json, sys, time
from collections import deque
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enumerate_class as E  # noqa: E402
from src.lrx.state import apply_L, apply_R, apply_X  # noqa: E402
from src.lrx.certificates import replay_visible  # noqa: E402

M = 9


def rank_vec(pos, n, w):
    """Vectorized Lehmer rank of position arrays pos[9,N] (independent of compute())."""
    mask = np.zeros(pos.shape[1], dtype=np.int64)
    rk = np.zeros(pos.shape[1], dtype=np.int64)
    for i in range(pos.shape[0]):
        p = pos[i]
        below = np.bitwise_count(mask & (np.left_shift(1, p) - 1)).astype(np.int64)
        rk += (p - below) * w[i]
        mask |= np.left_shift(1, p)
    return rk


def word_for(t, v):
    """Greedy descent in the exact table: returns a shortest sorting word of v."""
    word = []
    d = t.distance(v)
    moves = (("L", apply_L), ("R", apply_R), ("X", apply_X))
    while d:
        for name, f in moves:
            w = f(v)
            if t.distance(w) == d - 1:
                word.append(name)
                v, d = w, d - 1
                break
        else:
            raise RuntimeError("no descending neighbour")
    return "".join(word)


def bfs_dict(m, r):
    root = tuple(range(1, m + 1)) + (0,) * r
    dist = {root: 0}
    dq = deque([root])
    while dq:
        v = dq.popleft()
        for f in (apply_L, apply_R, apply_X):
            w = f(v)
            if w not in dist:
                dist[w] = dist[v] + 1
                dq.append(w)
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("r", type=int)
    ap.add_argument("--symmetry-sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=260925)
    ap.add_argument("--dict-bfs", action="store_true")
    ap.add_argument("--word-cap", type=int, default=500)
    a = ap.parse_args()
    r = a.r
    n, p, P, c, T9 = E.params(r)
    t0 = time.time()
    t8, t9, _, _ = E.setup(r)
    full = HERE / f"class_m9_r{r}_full.json"
    res_path = full if full.exists() else HERE / f"class_m9_r{r}_sample.json"
    res = json.loads(res_path.read_text())
    out = {"r": r, "source": res_path.name}
    ntot = len(t9.dist)
    rng = np.random.default_rng(a.seed)
    bits = None
    if "class_bitmap" in res:
        blob = (E.ROOT / res["class_bitmap"]["path"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == res["class_bitmap"]["sha256"]
        bits = np.unpackbits(np.frombuffer(blob, dtype=np.uint8))[:ntot].astype(bool)
        assert int(bits.sum()) == res["class_size"]
        members = np.flatnonzero(bits)
        pick = rng.choice(members, size=min(1000, members.size), replace=False)
    else:
        pick = None
    # 1. cross-check 1000 random class members with the pure-Python Ranker path
    if pick is not None:
        rk9 = t9.ranker
        bad = 0
        for code in pick.tolist():
            v = rk9.vector(rk9.unrank(code))
            ds = [t8.distance(tuple(x if x < q else x - 1 for x in v if x != q)) for q in range(1, M + 1)]
            if not all(P - c < d <= P for d in ds):
                bad += 1
        out["crosscheck_class_members"] = {"checked": len(pick), "violations": bad, "seed": a.seed,
                                           "method": "DistanceTable (sha256-verified reload) + pure-Python Ranker on explicit deleted vectors"}
    # 2. independent dict BFS (small r only)
    if a.dict_bfs:
        for (m, rr), t in (((M - 1, r), t8), ((M, r), t9)):
            dist = bfs_dict(m, rr)
            mism = sum(1 for v, d in dist.items() if t.distance(v) != d)
            out[f"dict_bfs_m{m}_r{rr}"] = {"states": len(dist), "mismatches": mism, "radius": max(dist.values())}
    # 3. symmetry tests on candidate maps g_{k,refl,comp}(v) = L^k(kappa^comp(psi^refl(v)))
    if bits is not None:
        if a.symmetry_sample:
            codes = rng.integers(0, ntot, size=a.symmetry_sample, dtype=np.int64)
            scope = f"random sample N={a.symmetry_sample} seed={a.seed}"
        else:
            codes = np.arange(ntot, dtype=np.int64)
            scope = "all states"
        _, dv, pos = E.compute(codes)
        cls = bits[codes]
        w9 = E.G["w9"]
        assert (rank_vec(pos, n, w9) == codes).all()
        sym = []
        for refl in (0, 1):
            for comp in (0, 1):
                for k in range(n):
                    q = pos.copy()
                    if refl:
                        q = (1 - q) % n
                    if comp:
                        q = q[::-1]
                    q = (q - k) % n
                    img = rank_vec(q, n, w9)
                    dimg = E.G["d9"][img]
                    sym.append({"k": k, "reflect": refl, "complement": comp,
                                "d_preserved_frac": float((dimg == dv).mean()),
                                "class_to_class_frac": float(bits[img][cls].mean()),
                                "class_preserved_both_ways": bool((bits[img] == cls).all())})
        out["symmetry"] = {"scope": scope, "maps": sym,
                           "exact_d_preserving": [s for s in sym if s["d_preserved_frac"] == 1.0],
                           "class_closed": [s for s in sym if s["class_preserved_both_ways"]]}
    # 4. literal sorting words for extremal class states (and the note's example at r=1)
    targets = [tuple(s["v"]) for s in res["argmax_cls"]][: a.word_cap]
    if r == 1:
        targets.append((0, 9, 8, 7, 6, 5, 4, 3, 2, 1))
    words = []
    root = tuple(range(1, M + 1)) + (0,) * r
    for v in targets:
        w = word_for(t9, v)
        ok = replay_visible(v, w) == root
        rk9 = t9.ranker
        ds = [t8.distance(tuple(x if x < q else x - 1 for x in v if x != q)) for q in range(1, M + 1)]
        words.append({"v": v, "d": t9.distance(v), "word_len": len(w), "replay_ok": ok, "word": w, "d_q": ds})
    out["words"] = words
    out["words_all_ok"] = all(x["replay_ok"] and x["word_len"] == x["d"] for x in words)
    out["wall_seconds"] = round(time.time() - t0, 1)
    dst = HERE / f"check_m9_r{r}.json"
    if dst.exists():
        raise FileExistsError(dst)
    dst.write_text(json.dumps(out, indent=1) + "\n")
    summ = {k: v for k, v in out.items() if k not in ("symmetry", "words")}
    if "symmetry" in out:
        summ["sym_exact_d"] = [(s["k"], s["reflect"], s["complement"]) for s in out["symmetry"]["exact_d_preserving"]]
        summ["sym_class_closed"] = [(s["k"], s["reflect"], s["complement"]) for s in out["symmetry"]["class_closed"]]
        best = sorted(out["symmetry"]["maps"], key=lambda s: -s["d_preserved_frac"])[:4]
        summ["sym_best_nonexact"] = best
    summ["n_words"] = len(words)
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
