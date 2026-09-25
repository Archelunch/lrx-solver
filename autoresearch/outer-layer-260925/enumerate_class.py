"""Exact enumeration of the outer-layer class C(9,r) of the linear outer-layer note.

For every visible state v of the (9,r) graph (all n!/r! ranks, n=9+r) compute the
nine single-label deletion distances d_q(v) = d(delta_q v, u0) from the exact (8,r)
table and d(v,v0) from the exact (9,r) table.

    p = n-1, P = T_8(n-1) = 30+6r, c_p = ceil(11p/4)-1
    proved by Theorem 2 alone:  min_q d_q(v) <= P-c_p
    class C(9,r) (condition (6)):  P-c_p < d_q(v) <= P for all q

Deletion-rank identity (Lehmer digits c_i of label i over positions p_i):
deleting label q and renumbering gives digits c'_i = c_i - [p_i > p_q] for i<q
and c'_i = c_i for i>q (self-checked against table_bfs.Ranker at startup).

Usage: python enumerate_class.py r [--sample N --seed S]
"""
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.lrx.table_bfs import DistanceTable, Ranker  # noqa: E402

WORK = Path(__file__).resolve().parent
LOCKED = ROOT / "datasets/generated"
NEW = ROOT / "datasets/generated/outer-layer-260925"
LOCK = json.loads((ROOT / "datasets/tables.lock.json").read_text())
M = 9


def load(m, r):
    key = f"m{m}_r{r}"
    if key in LOCK:
        t = DistanceTable(LOCKED, m, r)  # verifies sha256 against its json
        assert t.meta["table_sha256"] == LOCK[key], key
        src = str(LOCKED)
    else:
        t = DistanceTable(NEW, m, r)
        src = str(NEW)
    return t, src


def params(r):
    n = M + r
    p = n - 1
    P = math.comb(M - 1, 2) + 2 + (M - 3) * r
    c = -(-11 * p // 4) - 1
    T9 = M * (M + 1) // 2 + (r - 1) * (M - 2)
    assert T9 == P + p
    return n, p, P, c, T9


G = {}


def setup(r):
    n = M + r
    t8, s8 = load(M - 1, r)
    t9, s9 = load(M, r)
    G["d8"] = np.frombuffer(t8.dist, dtype=np.uint8)
    G["d9"] = np.frombuffer(t9.dist, dtype=np.uint8)
    G["w9"] = np.array(Ranker(M, r).weights, dtype=np.int64)
    G["w8"] = np.array(Ranker(M - 1, r).weights, dtype=np.int64)
    G["rad9"] = np.array([n - i for i in range(M)], dtype=np.int64)
    # select table: sel[mask, c] = position of the c-th free slot of mask
    size = 1 << n
    sel = np.full((size, n), -1, dtype=np.int8)
    for mask in range(size):
        free = [s for s in range(n) if not (mask >> s) & 1]
        sel[mask, : len(free)] = free
    G["sel"] = sel
    G["r"], G["n"] = r, n
    return t8, t9, s8, s9


def compute(codes):
    """Return (D[9,N] deletion distances, dv[N], pos[N,9]) for rank array codes."""
    w9, w8, sel = G["w9"], G["w8"], G["sel"]
    N = codes.shape[0]
    dig = np.empty((M, N), dtype=np.int64)
    pos = np.empty((M, N), dtype=np.int64)
    mask = np.zeros(N, dtype=np.int64)
    for i in range(M):
        dig[i] = (codes // w9[i]) % G["rad9"][i]
        pos[i] = sel[mask, dig[i]]
        mask |= np.left_shift(1, pos[i])
    D = np.empty((M, N), dtype=np.uint8)
    for q in range(M):
        rk = np.zeros(N, dtype=np.int64)
        k = 0
        for i in range(M):
            if i == q:
                continue
            ci = dig[i] - (pos[i] > pos[q]) if i < q else dig[i]
            rk += ci * w8[k]
            k += 1
        D[q] = G["d8"][rk]
    dv = G["d9"][codes]
    return D, dv, pos


def work(args):
    lo, hi, lim, P, c = args
    codes = np.arange(lo, hi, dtype=np.int64)
    return stats(codes, P, c, lim, bitmap=True)


def stats(codes, P, c, lim, bitmap):
    D, dv, _ = compute(codes)
    mn, mx = D.min(0), D.max(0)
    out = {}
    out["hmin"] = np.bincount(mn, minlength=256)
    out["hmax"] = np.bincount(mx, minlength=256)
    out["h_min_dv"] = np.bincount(mn.astype(np.int64) * 256 + dv, minlength=65536)
    proved = mn <= P - c
    cls = (mn > P - c) & (mx <= P)
    out["proved"] = int(proved.sum())
    out["above_P"] = int((mx > P).sum())
    out["unreached"] = int((dv == 255).sum() + (D == 255).sum())
    out["n"] = int(codes.shape[0])
    out["cls"] = int(cls.sum())
    out["h_cls_dv"] = np.bincount(dv[cls], minlength=256)
    out["h_proved_dv"] = np.bincount(dv[proved], minlength=256)
    for name, sel_ in (("cls", cls), ("proved", proved)):
        if sel_.any():
            top = int(dv[sel_].max())
            hit = codes[sel_ & (dv == top)]
            out[f"top_{name}"] = (top, int(hit.shape[0]), hit[:lim].tolist())
        else:
            out[f"top_{name}"] = (-1, 0, [])
    if bitmap:
        out["bits"] = np.packbits(cls).tobytes()
    return out


def merge(acc, o, lim):
    if acc is None:
        return o
    for k in ("hmin", "hmax", "h_min_dv", "h_cls_dv", "h_proved_dv"):
        acc[k] = acc[k] + o[k]
    for k in ("proved", "above_P", "unreached", "n", "cls"):
        acc[k] += o[k]
    for k in ("top_cls", "top_proved"):
        a, b = acc[k], o[k]
        if b[0] > a[0]:
            acc[k] = b
        elif b[0] == a[0] and b[0] >= 0:
            acc[k] = (a[0], a[1] + b[1], (a[2] + b[2])[:lim])
    return acc


def selfcheck(t8, t9, r, P, c, trials=3000, seed=12345):
    rng = np.random.default_rng(seed)
    codes = rng.integers(0, len(t9.dist), size=trials, dtype=np.int64)
    D, dv, _ = compute(codes)
    rk9 = t9.ranker
    for j, code in enumerate(codes.tolist()):
        v = rk9.vector(rk9.unrank(code))
        assert t9.distance(v) == dv[j]
        for q in range(1, M + 1):
            u = tuple(x if x < q else x - 1 for x in v if x != q)
            assert t8.distance(u) == D[q - 1, j], (v, q)
    return trials


def hist_dict(h):
    return {int(i): int(x) for i, x in enumerate(h) if x}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("r", type=int)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=260925)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--lim", type=int, default=500)
    a = ap.parse_args()
    r = a.r
    n, p, P, c, T9 = params(r)
    t0 = time.time()
    t8, t9, s8, s9 = setup(r)
    ntot = len(t9.dist)
    checked = selfcheck(t8, t9, r, P, c)
    acc = None
    bitmap_path = None
    if a.sample:
        rng = np.random.default_rng(a.seed)
        codes = rng.integers(0, ntot, size=a.sample, dtype=np.int64)
        for i in range(0, a.sample, 2_000_000):
            acc = merge(acc, stats(codes[i : i + 2_000_000], P, c, a.lim, False), a.lim)
        mode = f"uniform random sample with replacement, N={a.sample}, numpy default_rng seed={a.seed}"
    else:
        step = 1 << 21
        jobs = [(lo, min(lo + step, ntot), a.lim, P, c) for lo in range(0, ntot, step)]
        bitmap_path = NEW / f"class_bitmap_m9_r{r}.bin"
        import multiprocessing
        with multiprocessing.get_context("fork").Pool(a.workers) as pool, open(bitmap_path, "wb") as fh:
            for o in pool.imap(work, jobs):
                fh.write(o.pop("bits"))
                acc = merge(acc, o, a.lim)
        mode = "full enumeration of all ranks"
    wall = time.time() - t0
    rk = t9.ranker
    res = {
        "m": M, "r": r, "n": n, "p": p, "P": P, "c_p": c, "P_minus_c": P - c, "T9": T9,
        "mode": mode, "states_total": ntot, "states_examined": acc["n"],
        "radius_8r": t8.radius, "radius_9r": t9.radius,
        "table_8r": {"dir": s8, "sha256": t8.meta["table_sha256"]},
        "table_9r": {"dir": s9, "sha256": t9.meta["table_sha256"]},
        "selfcheck_states_vs_Ranker": checked,
        "proved_by_theorem2": acc["proved"],
        "class_size": acc["cls"],
        "other_max_above_P": acc["above_P"],
        "unreached_entries": acc["unreached"],
        "hist_min_dq": hist_dict(acc["hmin"]),
        "hist_max_dq": hist_dict(acc["hmax"]),
        "hist_dv_class": hist_dict(acc["h_cls_dv"]),
        "hist_dv_proved": hist_dict(acc["h_proved_dv"]),
        "hist_slack_class": {int(T9 - k): v for k, v in hist_dict(acc["h_cls_dv"]).items()},
        "hist_min_dq_by_dv": {f"{k // 256},{k % 256}": int(x) for k, x in enumerate(acc["h_min_dv"]) if x},
        "wall_seconds": round(wall, 1),
    }
    for name in ("cls", "proved"):
        top, cnt, codes = acc[f"top_{name}"]
        D, dv, _ = compute(np.array(codes, dtype=np.int64)) if codes else (None, None, None)
        res[f"max_dv_{name}"] = top
        res[f"argmax_count_{name}"] = cnt
        res[f"argmax_{name}"] = [
            {"rank": cd, "v": rk.vector(rk.unrank(cd)), "d_q": D[:, j].tolist()}
            for j, cd in enumerate(codes)
        ]
    res["class_all_within_T9"] = res["max_dv_cls"] <= T9
    if bitmap_path:
        blob = bitmap_path.read_bytes()
        res["class_bitmap"] = {"path": str(bitmap_path.relative_to(ROOT)), "sha256": hashlib.sha256(blob).hexdigest(),
                               "format": "np.packbits(big-endian bit order) over ranks 0..states-1"}
    suffix = "sample" if a.sample else "full"
    out = WORK / f"class_m9_r{r}_{suffix}.json"
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("r", "P", "c_p", "P_minus_c", "T9", "states_examined", "proved_by_theorem2",
                                           "class_size", "other_max_above_P", "max_dv_cls", "argmax_count_cls",
                                           "max_dv_proved", "radius_8r", "radius_9r", "wall_seconds")}))


if __name__ == "__main__":
    main()
