"""Fast exact check of the manuscript's lifting candidate A_P(v) <= P + m - 2.

Manuscript (references/source-manifest.md, section 6):
    P = E_{r-1}(n-1),  A_P(v) = min_{j: v_j = 0} F_{P - d(v\\j)}(v\\j, j),
and "A_P(v) <= P + m - 2 for all v" would give recursion (1),
E_r(n) <= E_{r-1}(n-1) + m - 2. Equivalently A_P(v) = min_j H_P(v\\j, j): the
shortest LRX word from v to the root whose projection (the word seen after
deleting the marked zero j) has at most P letters. This module computes H_q
exactly with numpy for all marked states, then A_q for all visible states.
It is the same quantity as `evaluate.evaluate_projection` (pure Python,
small graphs only) and is cross-checked against it in tests.

Marked states are arrangements of {1..m, M=m+1, 0^(r-1)} where M is the
marked zero, ranked like table_bfs.Ranker(m+1, r-1). A move changes the
projection unless it only moves M next to the cursor: L with M at 0, R with M
at n-1, X with M at 0 or 1. Self-loops (X on two plain zeros) are dropped.

Infinity (no admissible lift) is reported only after the complete
computation; memory refusals raise MemoryError before allocation.
"""

import math
import time

import numpy as np

from .table_bfs import Ranker, build_table

INF = np.int16(30000)


def _tables(n):
    if n > 16:
        raise ValueError("lifting_fast supports n <= 16")
    size = 1 << n
    popcount = np.array([bin(i).count("1") for i in range(size)], dtype=np.int8)
    select = np.full((size, n), -1, dtype=np.int8)
    for mask in range(size):
        bits = [b for b in range(n) if mask >> b & 1]
        select[mask, : len(bits)] = bits
    return popcount, select


class _Space:
    """Vectorised rank/unrank for arrangements of `k` distinct tokens in n slots."""

    def __init__(self, k, n, popcount, select):
        self.k, self.n = k, n
        self.size = math.perm(n, k)
        weights = [1] * k
        for i in range(k - 2, -1, -1):
            weights[i] = weights[i + 1] * (n - i - 1)
        self.weights = np.array(weights, dtype=np.int64)
        self.popcount, self.select = popcount, select

    def unrank(self, codes):
        codes = codes.astype(np.int64)
        free = np.full(len(codes), (1 << self.n) - 1, dtype=np.int64)
        pos = np.empty((len(codes), self.k), dtype=np.int8)
        for i in range(self.k):
            c = (codes // self.weights[i]) % (self.n - i)
            p = self.select[free, c]
            pos[:, i] = p
            free &= ~(np.int64(1) << p.astype(np.int64))
        return pos

    def rank(self, pos):
        total = np.zeros(len(pos), dtype=np.int64)
        used = np.zeros(len(pos), dtype=np.int64)
        for i in range(self.k):
            p = pos[:, i].astype(np.int64)
            below = self.popcount[used & ((np.int64(1) << p) - 1)].astype(np.int64)
            total += (p - below) * self.weights[i]
            used |= np.int64(1) << p
        return total


def estimate_bytes(m, r, keep_layers):
    size = math.perm(m + r, m + 1)
    base = size * (3 * 4 + 3 + 2 * 2) + math.perm(m + r, m) * 2
    return base + (size * keep_layers if keep_layers else 0)


def build_transitions(m, r, chunk=2_000_000):
    """Neighbour ranks and projection-change flags for every marked state."""
    n = m + r
    popcount, select = _tables(n)
    space = _Space(m + 1, n, popcount, select)
    lmap = np.array([(p - 1) % n for p in range(n)], dtype=np.int8)
    rmap = np.array([(p + 1) % n for p in range(n)], dtype=np.int8)
    xmap = np.array([{0: 1, 1: 0}.get(p, p) for p in range(n)], dtype=np.int8)
    size = space.size
    targets = np.empty((3, size), dtype=np.int32 if size < 2**31 else np.int64)
    changes = np.empty((3, size), dtype=bool)
    for start in range(0, size, chunk):
        codes = np.arange(start, min(size, start + chunk), dtype=np.int64)
        pos = space.unrank(codes)
        marked = pos[:, m]
        for k, table in enumerate((lmap, rmap, xmap)):
            targets[k, start : start + len(codes)] = space.rank(table[pos])
        changes[0, start : start + len(codes)] = marked != 0
        changes[1, start : start + len(codes)] = marked != n - 1
        changes[2, start : start + len(codes)] = (marked != 0) & (marked != 1)
    own = np.arange(size, dtype=targets.dtype)
    loops = targets == own[None, :]
    changes &= ~loops
    return space, targets, changes, loops


def _terminal_mask(space, m, r):
    n = m + r
    mask = np.zeros(space.size, dtype=bool)
    for j in range(m, n):
        pos = np.array([list(range(m)) + [j]], dtype=np.int8)
        mask[space.rank(pos)[0]] = True
    return mask


def h_layers(m, r, q, keep_layers=False, transitions=None, log=None):
    """Return (H_q array over marked ranks, list of layers or None, transitions)."""
    space, targets, changes, loops = transitions or build_transitions(m, r)
    terminal = _terminal_mask(space, m, r)
    init = np.where(terminal, np.int16(0), INF).astype(np.int16)
    free_edges = [(k, np.nonzero(~changes[k] & ~loops[k])[0]) for k in range(3)]

    def closure(values):
        # Projection-free moves keep M within {0, 1, n-1}: path of length 2.
        for _ in range(2):
            for k, idx in free_edges:
                cand = values[targets[k, idx]] + 1
                values[idx] = np.minimum(values[idx], cand)
        return values

    layers = []
    current = closure(init.copy())
    if keep_layers:
        layers.append(current.copy())
    for level in range(1, q + 1):
        start = time.perf_counter()
        nxt = init.copy()
        for k in range(3):
            idx = changes[k]
            cand = current[targets[k][idx]] + 1
            nxt[idx] = np.minimum(nxt[idx], cand)
        np.minimum(nxt, INF, out=nxt)
        current = closure(nxt)
        if keep_layers:
            layers.append(current.copy())
        if log:
            log(f"layer {level}/{q} {time.perf_counter() - start:.1f}s")
    return current, (layers if keep_layers else None), (space, targets, changes, loops)


def lift_values(m, r, q, keep_layers=False, log=None):
    """A_q(v) for every visible v (ranked like table_bfs.Ranker(m, r))."""
    h, layers, trans = h_layers(m, r, q, keep_layers=keep_layers, log=log)
    space = trans[0]
    n = m + r
    visible = _Space(m, n, space.popcount, space.select)
    a = np.full(visible.size, INF, dtype=np.int16)
    chunk = 4_000_000
    for start in range(0, space.size, chunk):
        codes = np.arange(start, min(space.size, start + chunk), dtype=np.int64)
        pos = space.unrank(codes)
        vis = visible.rank(pos[:, :m])
        np.minimum.at(a, vis, h[start : start + len(codes)])
    return a, h, layers, trans


def witness(m, r, q, layers, trans, marked_code):
    """Reconstruct one optimal lift word for a marked state from stored layers."""
    space, targets, changes, loops = trans
    word = []
    code, budget = int(marked_code), q
    remaining = int(layers[budget][code])
    names = "LRX"
    while remaining:
        for k in range(3):
            if loops[k, code]:
                continue
            tgt = int(targets[k, code])
            nb = budget - int(changes[k, code])
            if nb >= 0 and int(layers[nb][tgt]) == remaining - 1:
                word.append(names[k])
                code, budget, remaining = tgt, nb, remaining - 1
                break
        else:
            raise AssertionError("no reconstructible witness")
    return "".join(word)


def check_graph(m, r, q=None, keep_layers=False, examples=5, log=None):
    """Exhaustive A_q <= q + m - 2 check. Returns a JSON-serialisable report."""
    start = time.perf_counter()
    smaller, smeta = build_table(m, r - 1, workers=1 if m + r <= 10 else 8)
    if not smeta["complete"]:
        raise RuntimeError("smaller BFS incomplete")
    p = smeta["radius"]
    q = p if q is None else q
    cap = q + m - 2
    a, h, layers, trans = lift_values(m, r, q, keep_layers=keep_layers, log=log)
    finite = a < INF
    over = finite & (a > cap)
    report = {
        "m": m,
        "r": r,
        "n": m + r,
        "smaller_radius_P": p,
        "projection_cap_q": q,
        "lift_budget": cap,
        "conjectured_T": m * (m + 1) // 2 + (r - 1) * (m - 2),
        "visible_states": int(a.size),
        "marked_states": int(h.size),
        "no_admissible_lift": int((~finite).sum()),
        "finite_over_budget": int(over.sum()),
        "max_finite_A": int(a[finite].max()) if finite.any() else None,
        "histogram_A_minus_cap": {
            str(k): int(v)
            for k, v in zip(*np.unique(a[finite].astype(int) - cap, return_counts=True))
            if k >= -3
        },
        "status": "COMPLETE",
        "scope": "finite: this graph only",
    }
    report["lifting_bound_holds_on_this_graph"] = (
        report["no_admissible_lift"] == 0 and report["finite_over_budget"] == 0
    )
    # Internal consistency with exact distances: A(v) is a word length, so A >= d.
    dist, dmeta = build_table(m, r, workers=1 if m + r <= 10 else 8)
    d = np.frombuffer(bytes(dist), dtype=np.uint8).astype(np.int16)
    report["true_radius"] = dmeta["radius"]
    report["A_below_distance_violations"] = int((finite & (a < d)).sum())
    report["A_equals_distance"] = int((finite & (a == d)).sum())
    worst = np.argsort(-np.where(finite, a, -1))[:examples]
    ranker = Ranker(m, r)
    report["worst"] = []
    for code in worst:
        entry = {
            "v": list(ranker.vector(ranker.unrank(int(code)))),
            "A": int(a[code]),
            "d": int(d[code]),
        }
        report["worst"].append(entry)
    report["seconds"] = round(time.perf_counter() - start, 1)
    if keep_layers and layers is not None:
        report["_layers"] = layers
        report["_trans"] = trans
        report["_h"] = h
    return report
