"""Low-memory layered BFS for large (m, r) visible-distance tables.

Produces byte-identical output to src.lrx.table_bfs.write_table (same
Ranker, same .bin layout, same meta fields plus table_sha256), but keeps
peak resident memory low by using on-disk numpy memmaps instead of
in-RAM Python structures:

- dist: a uint8 memmap of size n!/r! (255 = unvisited), written in place.
- frontier / next-frontier: bit-packed uint8 memmaps of size ceil(N/8).

Design (why races cannot corrupt the frontier):
- The rank space [0, N) is split ONCE, at build start, into `workers`
  fixed, disjoint, byte-aligned contiguous ranges. Every layer, worker i
  only ever reads frontier bits in its own range [lo_i, hi_i).
- Each worker writes newly-discovered neighbour ranks into a PRIVATE
  next-frontier bitmap file (one file per worker per layer). No two
  processes ever write to the same next-frontier file, so there is no
  frontier race at all -- not "usually safe", structurally impossible.
  The parent process ORs the private files together after the pool
  synchronizes (Pool.starmap blocks until every worker returns), which
  is a single-threaded, race-free merge step.
- The dist[] array IS shared (memmap opened r+ in every worker, inherited
  via fork). Multiple workers can concurrently write dist[code] = d1 for
  the same code in the same layer, but only ever the same value d1 (a
  worker only writes a byte that it just observed as 255/unvisited; once
  written it becomes the true distance for the rest of the run since
  distances only increase). A single aligned uint8 store is atomic on
  x86-64 and ARM64, so concurrent identical writes cannot tear. Workers
  never write two different distance values to the same address in the
  same layer, so ordering across processes is irrelevant.
"""

import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np

from src.lrx.table_bfs import Ranker, source_hash, table_paths

UNREACHED = 255


def _byte_aligned_ranges(n_bits, workers):
    """Split [0, n_bits) into `workers` contiguous, byte-aligned ranges."""
    n_bytes = (n_bits + 7) // 8
    step = max(1, n_bytes // workers)
    bounds = [min(i * step * 8, n_bits) for i in range(workers)]
    bounds.append(n_bits)
    bounds[-1] = n_bits
    ranges = []
    for i in range(workers):
        lo, hi = bounds[i], bounds[i + 1] if i + 1 < len(bounds) else n_bits
        if i == workers - 1:
            hi = n_bits
        ranges.append((lo, hi))
    # de-duplicate any empty trailing ranges when workers > n_bytes
    return [r for r in ranges if r[1] > r[0]] or [(0, n_bits)]


def _worker_expand(args):
    (m, r, dist_path, n_states, frontier_path, lo, hi, d1, next_path) = args
    ranker = Ranker(m, r)
    n_bits = n_states
    n_bytes = (n_bits + 7) // 8
    dist = np.memmap(dist_path, dtype=np.uint8, mode="r+", shape=(n_states,))
    frontier = np.memmap(frontier_path, dtype=np.uint8, mode="r", shape=(n_bytes,))

    byte_lo, byte_hi = lo // 8, (hi + 7) // 8
    chunk = np.unpackbits(frontier[byte_lo:byte_hi], bitorder="little")
    local_bits = chunk[: hi - lo] if len(chunk) >= hi - lo else chunk
    local_idx = np.flatnonzero(local_bits)
    codes = (local_idx + lo).astype(np.int64)

    nf = np.memmap(next_path, dtype=np.uint8, mode="w+", shape=(n_bytes,))
    nf[:] = 0

    rank, unrank, neighbours = ranker.rank, ranker.unrank, ranker.neighbours
    processed = 0
    for code in codes.tolist():
        pos = unrank(code)
        for q in neighbours(pos):
            nb = rank(q)
            if dist[nb] == UNREACHED:
                dist[nb] = d1
                nf[nb >> 3] |= 1 << (nb & 7)
        processed += 1
    dist.flush()
    nf.flush()
    del dist, frontier, nf
    return processed


def _popcount_file(path, n_bytes, block=1 << 24):
    total = 0
    with open(path, "rb") as f:
        while True:
            buf = f.read(block)
            if not buf:
                break
            total += int(np.unpackbits(np.frombuffer(buf, dtype=np.uint8)).sum())
    return total


def _or_merge(paths, out_path, n_bytes, block=1 << 24):
    handles = [open(p, "rb") for p in paths]
    with open(out_path, "wb") as out:
        while True:
            bufs = [h.read(block) for h in handles]
            if not bufs[0]:
                break
            acc = np.frombuffer(bufs[0], dtype=np.uint8).copy()
            for b in bufs[1:]:
                if b:
                    acc |= np.frombuffer(b, dtype=np.uint8)
            out.write(acc.tobytes())
    for h in handles:
        h.close()


def build_table_lowmem(m, r, out_dir, workers=1, log_path=None, chunk=None):
    """Build the (m, r) distance table with bounded peak RAM.

    Returns the meta dict (as written to the .json sidecar). Writes
    dist_m{m}_r{r}.bin/.json into out_dir in the exact format produced by
    src.lrx.table_bfs.write_table.
    """
    ranker = Ranker(m, r)
    n = ranker.size
    n_bytes = (n + 7) // 8
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bin_path, meta_path = table_paths(out_dir, m, r)
    if bin_path.exists() or meta_path.exists():
        raise FileExistsError(f"refusing to overwrite {bin_path}")

    work_dir = out_dir / f".lowmem_m{m}_r{r}"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_path = work_dir / "dist.tmp"
    dist = np.memmap(dist_path, dtype=np.uint8, mode="w+", shape=(n,))
    dist[:] = UNREACHED

    root = ranker.rank(ranker.positions(ranker.root()))
    dist[root] = 0
    dist.flush()

    frontier_path = work_dir / "frontier_0.bits"
    frontier = np.memmap(frontier_path, dtype=np.uint8, mode="w+", shape=(n_bytes,))
    frontier[:] = 0
    frontier[root >> 3] |= 1 << (root & 7)
    frontier.flush()
    del frontier

    ranges = _byte_aligned_ranges(n, workers)
    start = time.perf_counter()
    layers = [1]
    depth = 0
    log_f = open(log_path, "a") if log_path else None
    try:
        pool = None
        if workers > 1:
            import multiprocessing

            pool = multiprocessing.get_context("fork").Pool(workers)
        try:
            while True:
                if depth + 1 >= UNREACHED:
                    raise OverflowError("distance exceeds one-byte table")
                d1 = depth + 1
                next_paths = [
                    work_dir / f"next_{depth}_{i}.bits" for i in range(len(ranges))
                ]
                tasks = [
                    (m, r, str(dist_path), n, str(frontier_path), lo, hi, d1, str(np))
                    for (lo, hi), np in zip(ranges, next_paths)
                ]
                if pool is None:
                    list(map(_worker_expand, tasks))
                else:
                    pool.map(_worker_expand, tasks)

                merged_path = work_dir / f"frontier_{depth + 1}.bits"
                _or_merge([str(p) for p in next_paths], merged_path, n_bytes)
                for p in next_paths:
                    p.unlink(missing_ok=True)
                Path(frontier_path).unlink(missing_ok=True)
                frontier_path = merged_path

                layer_size = _popcount_file(frontier_path, n_bytes)
                elapsed = time.perf_counter() - start
                line = f"layer={d1} frontier={layer_size} elapsed={elapsed:.1f}s"
                if log_f:
                    log_f.write(line + "\n")
                    log_f.flush()
                if layer_size == 0:
                    break
                layers.append(layer_size)
                depth += 1
        finally:
            if pool is not None:
                pool.close()
                pool.join()
    finally:
        if log_f:
            log_f.close()

    Path(frontier_path).unlink(missing_ok=True)
    dist.flush()
    del dist

    total = sum(layers)
    meta = {
        "m": m,
        "r": r,
        "n": m + r,
        "states": n,
        "reached": total,
        "complete": total == n,
        "radius": len(layers) - 1,
        "layer_sizes": layers,
        "rank_scheme": "lehmer-positions-v1",
        "seconds": round(time.perf_counter() - start, 3),
        "workers": workers,
        "source_sha256": source_hash(),
    }

    digest = hashlib.sha256()
    with open(dist_path, "rb") as f:
        while True:
            buf = f.read(1 << 24)
            if not buf:
                break
            digest.update(buf)
    meta["table_sha256"] = digest.hexdigest()

    os.replace(dist_path, bin_path)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    try:
        work_dir.rmdir()
    except OSError:
        pass
    return meta
