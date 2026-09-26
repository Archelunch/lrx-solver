"""Ranked visible-state BFS with one-byte distance tables.

A visible state of (1..m, 0^r) is identified by the positions P=(p_1..p_m) of
tokens 1..m; zeros fill the rest. Rank is the mixed-radix Lehmer code of P over
radices (n, n-1, ..., n-m+1), a bijection onto [0, n!/r!).

Distances are measured from the canonical root, so the last nonempty layer is
the sorting radius E_r(n) (eccentricity of the root), not the graph diameter.
LRX is symmetric (R = L^-1, X involution), so root-to-v equals v-to-root.
"""

import hashlib
import json
import math
import os
import time
from array import array
from pathlib import Path

UNREACHED = 255


class Ranker:
    def __init__(self, m, r):
        if type(m) is not int or type(r) is not int or m < 1 or r < 0:
            raise ValueError("Require integer m >= 1, r >= 0")
        self.m, self.r, self.n = m, r, m + r
        n = self.n
        weights = [1] * m
        for i in range(m - 2, -1, -1):
            weights[i] = weights[i + 1] * (n - i - 1)
        self.weights = tuple(weights)
        self.size = math.perm(n, m)
        self.lmap = tuple((p - 1) % n for p in range(n))
        self.rmap = tuple((p + 1) % n for p in range(n))
        self.xmap = tuple({0: 1, 1: 0}.get(p, p) for p in range(n))

    def rank(self, pos):
        total = 0
        mask = 0
        for p, w in zip(pos, self.weights):
            total += (p - (mask & ((1 << p) - 1)).bit_count()) * w
            mask |= 1 << p
        return total

    def unrank(self, code):
        n = self.n
        free = list(range(n))
        pos = []
        for w in self.weights:
            c, code = divmod(code, w)
            pos.append(free.pop(c))
        return tuple(pos)

    def positions(self, v):
        if len(v) != self.n or sorted(v) != sorted(self.root()):
            raise ValueError("Vector does not match the multiset")
        pos = [0] * self.m
        for index, value in enumerate(v):
            if value:
                pos[value - 1] = index
        return tuple(pos)

    def vector(self, pos):
        v = [0] * self.n
        for token, p in enumerate(pos, 1):
            v[p] = token
        return tuple(v)

    def root(self):
        return tuple(range(1, self.m + 1)) + (0,) * self.r

    def neighbours(self, pos):
        lm, rm, xm = self.lmap, self.rmap, self.xmap
        return (
            tuple([lm[p] for p in pos]),
            tuple([rm[p] for p in pos]),
            tuple([xm[p] for p in pos]),
        )


def _expand_chunk(args):
    m, r, codes = args
    ranker = Ranker(m, r)
    rank, unrank, neighbours = ranker.rank, ranker.unrank, ranker.neighbours
    out = array("Q")
    for code in codes:
        for q in neighbours(unrank(code)):
            out.append(rank(q))
    return out


def source_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def estimate_bytes(m, r):
    size = math.perm(m + r, m)
    # distance table + worst-case frontier of 8-byte ranks (+ neighbour buffer).
    return size + 16 * size // 4


def build_table(m, r, workers=1, max_bytes=2 * 1024**3, chunk=20_000):
    """Return (dist bytearray, meta dict). Raises MemoryError when refused."""
    ranker = Ranker(m, r)
    need = estimate_bytes(m, r)
    if need > max_bytes:
        raise MemoryError(f"estimated {need} bytes exceeds max_bytes {max_bytes}")
    start = time.perf_counter()
    dist = bytearray([UNREACHED]) * ranker.size
    root = ranker.rank(ranker.positions(ranker.root()))
    dist[root] = 0
    frontier = array("Q", [root])
    layers = [1]
    pool = None
    if workers > 1:
        import multiprocessing

        pool = multiprocessing.get_context("fork").Pool(workers)
    try:
        depth = 0
        while frontier:
            if depth + 1 >= UNREACHED:
                raise OverflowError("distance exceeds one-byte table")
            nxt = array("Q")
            pieces = [frontier[i : i + chunk] for i in range(0, len(frontier), chunk)]
            if pool is None:
                results = map(_expand_chunk, ((m, r, p) for p in pieces))
            else:
                results = pool.imap(_expand_chunk, ((m, r, p) for p in pieces))
            d1 = depth + 1
            for found in results:
                for code in found:
                    if dist[code] == UNREACHED:
                        dist[code] = d1
                        nxt.append(code)
            if nxt:
                layers.append(len(nxt))
            frontier = nxt
            depth += 1
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    total = sum(layers)
    meta = {
        "m": m,
        "r": r,
        "n": m + r,
        "states": ranker.size,
        "reached": total,
        "complete": total == ranker.size,
        "radius": len(layers) - 1,
        "layer_sizes": layers,
        "rank_scheme": "lehmer-positions-v1",
        "seconds": round(time.perf_counter() - start, 3),
        "workers": workers,
        "source_sha256": source_hash(),
    }
    return dist, meta


def table_paths(directory, m, r):
    base = Path(directory)
    return base / f"dist_m{m}_r{r}.bin", base / f"dist_m{m}_r{r}.json"


def write_table(directory, m, r, dist, meta):
    bin_path, meta_path = table_paths(directory, m, r)
    if bin_path.exists() or meta_path.exists():
        raise FileExistsError(f"refusing to overwrite {bin_path}")
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(meta, table_sha256=hashlib.sha256(dist).hexdigest())
    tmp = bin_path.with_suffix(".tmp")
    tmp.write_bytes(dist)
    os.replace(tmp, bin_path)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return meta


class DistanceTable:
    """Read-only loaded table with integrity check."""

    def __init__(self, directory, m, r, verify=True):
        bin_path, meta_path = table_paths(directory, m, r)
        self.meta = json.loads(meta_path.read_text())
        self.dist = bin_path.read_bytes()
        if verify:
            digest = hashlib.sha256(self.dist).hexdigest()
            if digest != self.meta.get("table_sha256"):
                raise ValueError(f"table hash mismatch for m={m} r={r}")
        if not self.meta.get("complete"):
            raise ValueError("table is INCOMPLETE; not usable as ground truth")
        self.ranker = Ranker(m, r)
        self.m, self.r, self.n = m, r, m + r
        self.radius = self.meta["radius"]

    def distance(self, v):
        return self.dist[self.ranker.rank(self.ranker.positions(tuple(v)))]

    def states_at(self, d, limit=None):
        """Vectors at exact distance d, in rank order (deterministic)."""
        out = []
        start = 0
        byte = bytes([d])
        while limit is None or len(out) < limit:
            code = self.dist.find(byte, start)
            if code < 0:
                break
            out.append(self.ranker.vector(self.ranker.unrank(code)))
            start = code + 1
        return out

    def spread_at(self, d, k):
        """Up to k distinct states at distance d, spread across rank order."""
        byte = bytes([d])
        size = len(self.dist)
        codes = []
        for i in range(k):
            code = self.dist.find(byte, i * size // k)
            if code < 0:
                code = self.dist.find(byte)
            if code >= 0 and (not codes or code != codes[-1]):
                codes.append(code)
        return [self.vector_at(c) for c in sorted(set(codes))]

    def vector_at(self, code):
        return self.ranker.vector(self.ranker.unrank(code))
