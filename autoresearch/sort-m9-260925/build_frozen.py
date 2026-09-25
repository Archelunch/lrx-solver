"""Freeze the development and holdout state sets for sort-m9-260925 (offline tooling; numpy).

Per table: sha256-verify against its meta JSON (and datasets/tables.lock.json when
locked), count layers in chunks, allocate per-layer quotas (all states at the
table radius go to development; 180 of 300 over the top 10 layers, 120 over
layers 1..radius-10, equal shares with water-filling), then draw distinct
within-layer ordinals with random.Random(260925), development first. Holdout
states come from the same draw, so the sets are disjoint by construction.
Also writes control (c): one shortest word per development state by descent in
the exact table, replayed with certificates.replay_visible (reference only).

Usage: python autoresearch/sort-m9-260925/build_frozen.py   (refuses to overwrite frozen/;
rerun after the last table is built: cached per-table parts are reused)
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.lrx.certificates import replay_visible  # noqa: E402
from src.lrx.table_bfs import Ranker  # noqa: E402
from integrations.sort_evaluator import SCHEMA, aggregate, budget, root, score_state  # noqa: E402

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "frozen"
PARTS = HERE / "frozen-parts"  # per-table samples, deterministic; assembled once all exist
SEED, PER_TABLE, TOP_LAYERS, TOP_SHARE = 260925, 300, 10, 180
GEN = ROOT / "datasets" / "generated"
TABLES = {  # (m, r): directory, role
    (9, 1): (GEN / "outer-layer-260925", "dev+holdout"),
    (9, 2): (GEN, "dev+holdout"),
    (9, 3): (GEN, "dev+holdout"),
    (9, 4): (GEN / "outer-layer-260925", "dev+holdout"),
    (9, 5): (GEN / "outer-layer-260925", "dev+holdout"),
    (9, 6): (GEN / "sort-m9-260925", "holdout"),
    (10, 3): (GEN / "sort-m9-260925", "holdout"),
}
CHUNK = 1 << 24


def waterfill(total, caps):
    alloc = [0] * len(caps)
    left = total
    while left > 0:
        active = [i for i in range(len(caps)) if alloc[i] < caps[i]]
        if not active:
            break
        share = left // len(active)
        if share == 0:
            for i in sorted(active, reverse=True)[:left]:  # leftovers to the highest layers
                alloc[i] += 1
            break
        for i in active:
            add = min(share, caps[i] - alloc[i])
            alloc[i] += add
            left -= add
    return alloc


def quotas(sizes, radius, taken=None, top_forced=True):
    """Per-layer quota dict. taken: states already assigned (development) per layer."""
    taken = taken or {}
    caps = {d: sizes[d] - taken.get(d, 0) for d in range(1, radius + 1)}
    q = {d: 0 for d in caps}
    top = list(range(max(1, radius - TOP_LAYERS + 1), radius + 1))
    rest = list(range(1, top[0]))
    top_budget = TOP_SHARE
    if top_forced:
        q[radius] = min(caps[radius], TOP_SHARE)
        top_budget -= q[radius]
        top = top[:-1]
    elif taken:
        caps[radius] = 0  # every radius state is already in development
    for d, a in zip(top, waterfill(top_budget, [caps[d] for d in top])):
        q[d] = a
    for d, a in zip(rest, waterfill(PER_TABLE - TOP_SHARE, [caps[d] for d in rest])):
        q[d] = a
    return q


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def sample_table(m, r, directory, role, lock):
    meta = json.loads((directory / f"dist_m{m}_r{r}.json").read_text())
    path = directory / f"dist_m{m}_r{r}.bin"
    digest = sha_file(path)
    if digest != meta["table_sha256"] or not meta["complete"]:
        raise SystemExit(f"table ({m},{r}) hash mismatch or incomplete")
    if f"m{m}_r{r}" in lock and lock[f"m{m}_r{r}"] != digest:
        raise SystemExit(f"table ({m},{r}) differs from datasets/tables.lock.json")
    table = np.memmap(path, dtype=np.uint8, mode="r")
    radius = meta["radius"]
    counts = []
    for i in range(0, len(table), CHUNK):
        counts.append(np.bincount(table[i:i + CHUNK], minlength=256)[:radius + 1])
    sizes = [int(x) for x in np.sum(counts, axis=0)]
    if sizes != meta["layer_sizes"]:
        raise SystemExit(f"table ({m},{r}) layer counts disagree with meta")
    if role == "dev+holdout":
        dq = quotas(sizes, radius)
        hq = quotas(sizes, radius, taken=dq, top_forced=False)
    else:
        dq, hq = {d: 0 for d in range(1, radius + 1)}, quotas(sizes, radius)
    rng = random.Random(SEED)
    want = {}  # layer -> sorted list of (ordinal, set)
    for d in range(1, radius + 1):
        ords = rng.sample(range(sizes[d]), dq[d] + hq[d])
        want[d] = sorted([(o, "development") for o in ords[:dq[d]]] + [(o, "holdout") for o in ords[dq[d]:]])
    ranks = {"development": [], "holdout": []}
    seen = {d: 0 for d in want}
    ptr = {d: 0 for d in want}
    for ci, i in enumerate(range(0, len(table), CHUNK)):
        chunk = None
        for d in want:
            lo, hi = seen[d], seen[d] + int(counts[ci][d])
            need = []
            while ptr[d] < len(want[d]) and want[d][ptr[d]][0] < hi:
                need.append(want[d][ptr[d]])
                ptr[d] += 1
            if need:
                chunk = table[i:i + CHUNK] if chunk is None else chunk
                idx = np.flatnonzero(chunk == d)
                for o, which in need:
                    ranks[which].append((d, i + int(idx[o - lo])))
            seen[d] = hi
    ranker = Ranker(m, r)
    out = {}
    for which, items in ranks.items():
        states = []
        for d, code in sorted(items):
            v = ranker.vector(ranker.unrank(code))
            if int(table[ranker.rank(ranker.positions(v))]) != d:
                raise SystemExit("rank round trip failed")
            states.append({"id": f"m{m}r{r}-{code}", "m": m, "r": r, "v": list(v), "d": d, "budget": budget(m, r)})
        out[which] = states
    prov = {"m": m, "r": r, "path": str(path.relative_to(ROOT)), "table_sha256": digest, "radius": radius,
            "T_m(n)": budget(m, r), "states": meta["states"], "layer_sizes": sizes,
            "states_at_T": sizes[budget(m, r)] if budget(m, r) <= radius else 0,
            "development_per_layer": {d: q for d, q in dq.items() if q},
            "holdout_per_layer": {d: q for d, q in hq.items() if q}}
    return out, prov, table


def descend(table, ranker, v):
    word, cur = [], tuple(v)
    d = int(table[ranker.rank(ranker.positions(cur))])
    while d:
        for ch in "LRX":
            nxt = replay_visible(cur, ch)
            if int(table[ranker.rank(ranker.positions(nxt))]) == d - 1:
                word.append(ch)
                cur, d = nxt, d - 1
                break
        else:
            raise SystemExit("descent failed")
    return "".join(word)


def main():
    FROZEN.mkdir(exist_ok=True)
    targets = [FROZEN / x for x in ("development.json", "holdout.json", "manifest.json")]
    if any(p.exists() for p in targets):
        raise SystemExit("refusing to overwrite frozen sets")
    lock = json.loads((ROOT / "datasets" / "tables.lock.json").read_text())
    dev, hold, provenance, reference = [], [], [], []
    PARTS.mkdir(exist_ok=True)
    for (m, r), (directory, role) in TABLES.items():
        part = PARTS / f"m{m}r{r}.json"
        if not part.exists():
            if not (directory / f"dist_m{m}_r{r}.bin").exists():
                print(f"table ({m},{r}) not built yet; skipping", flush=True)
                continue
            out, prov, table = sample_table(m, r, directory, role, lock)
            ranker = Ranker(m, r)
            words = []
            for s in out["development"]:
                w = descend(table, ranker, s["v"])
                if replay_visible(tuple(s["v"]), w) != root(m, r) or len(w) != s["d"]:
                    raise SystemExit("reference word failed replay")
                words.append({"id": s["id"], "word": w})
            del table
            part.write_text(json.dumps({"out": out, "prov": prov, "reference": words}) + "\n")
        data = json.loads(part.read_text())
        out, prov = data["out"], data["prov"]
        dev += out["development"]
        hold += out["holdout"]
        provenance.append(prov)
        reference += data["reference"]
        print(json.dumps({k: prov[k] for k in ("m", "r", "radius", "T_m(n)", "states_at_T", "table_sha256")}),
              len(out["development"]), len(out["holdout"]), flush=True)
    if len(provenance) != len(TABLES):
        raise SystemExit("not every table is sampled yet; per-table parts are cached in frozen-parts/")
    if {s["id"] for s in dev} & {s["id"] for s in hold}:
        raise SystemExit("development and holdout overlap")
    common = {"schema": SCHEMA, "task": "sort-m9-260925", "seed": SEED}
    (FROZEN / "development.json").write_text(json.dumps(dict(common, set="development", states=dev)) + "\n")
    (FROZEN / "holdout.json").write_text(json.dumps(dict(common, set="holdout", states=hold)) + "\n")
    words = {x["id"]: x["word"] for x in reference}
    rows = [score_state(s, {"status": "ok"}, {"word": words[s["id"]], "seconds": 0.0, "cpu_seconds": 0.0}) for s in dev]
    ref = aggregate(rows)
    controls = HERE / "controls"
    controls.mkdir(exist_ok=True)
    (controls / "reference-optimal-development.json").write_text(json.dumps(
        {"note": "Control (c): exact shortest words by descent in the BFS tables. Reference upper bound, "
                 "not a candidate program.", "summary": {k: v for k, v in ref.items()}, "words": reference}) + "\n")
    manifest = {
        "schema": "lrx-sort-frozen-manifest-v1", "task": "sort-m9-260925", "seed": SEED,
        "files": {"development.json": sha_file(FROZEN / "development.json"),
                  "holdout.json": sha_file(FROZEN / "holdout.json")},
        "counts": {"development": len(dev), "holdout": len(hold)},
        "sampling": "per table 300 states: all radius states (development only), 180 over the top 10 layers, "
                    "120 over layers 1..radius-10; equal per-layer shares with water-filling; ordinals drawn "
                    "by random.Random(260925) per table, development first; see build_frozen.py",
        "tables": provenance,
        "reference_optimal_development": {k: ref[k] for k in ("within_fraction", "mean_excess", "combined_score")},
        "holdout_never_loaded_by": ["engines", "proposers", "sequential control", "smoke tests"],
        "note": "Holdout (m=9 r=1..5 disjoint from development, m=9 r=6, m=10 r=3) is evaluated once, after "
                "finalist freeze, by a human-run offline check; never by any engine, proposer, or smoke.",
    }
    (FROZEN / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest["files"]), json.dumps(manifest["counts"]))


if __name__ == "__main__":
    main()
