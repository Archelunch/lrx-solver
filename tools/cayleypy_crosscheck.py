"""Independent cross-check of lrx-lab tables with cayleypy.

Run with the external venv, never from the verifier:

    .venv-ext/bin/python tools/cayleypy_crosscheck.py [--beam] [--skip m9r3]

A. BFS: cayleypy's LRX coset graph with central state (1..m, 0^r); its layer
   sizes must equal the layer sizes in datasets/generated/*.json. Any mismatch
   is a bug report, not a result.
B. --beam: cayleypy beam search words from probe states of the table-less
   heldout graphs. Every word is replayed by src.lrx.certificates before it is
   recorded; a long or missing word is never a lower bound.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cayleypy  # noqa: E402
from cayleypy import CayleyGraph, PermutationGroups  # noqa: E402

from src.lrx.certificates import replay_visible  # noqa: E402
from src.lrx.dsl import budget  # noqa: E402
from src.lrx.evaluator import load_registry, paths, probe_states  # noqa: E402


def coset_graph(m, r):
    n = m + r
    root = list(range(1, m + 1)) + [0] * r
    return CayleyGraph(
        PermutationGroups.lrx(n).with_central_state(root), device="cpu"
    ), root


def check_bfs(g, table_dir):
    m, r = g["m"], g["r"]
    meta = json.loads((table_dir / f"dist_m{m}_r{r}.json").read_text())
    graph, _ = coset_graph(m, r)
    start = time.perf_counter()
    res = graph.bfs(max_layer_size_to_store=1)
    layers = [int(x) for x in res.layer_sizes]
    return {
        "graph": f"m{m}r{r}",
        "states": sum(layers),
        "cayleypy_radius": len(layers) - 1,
        "lrx_lab_radius": meta["radius"],
        "layer_sizes_equal": layers == meta["layer_sizes"],
        "seconds": round(time.perf_counter() - start, 2),
    }


def beam_words(g, width, max_starts):
    m, r = g["m"], g["r"]
    graph, root = coset_graph(m, r)
    names = graph.definition.generator_names
    rows = []
    for v in probe_states(g, load_registry()["probe"])[:max_starts]:
        res = graph.beam_search(
            start_state=list(v),
            beam_width=width,
            max_steps=10 * (m + r) ** 2,
            return_path=True,
        )
        if not res.path_found:
            rows.append({"v": list(v), "found": False})
            continue
        word = "".join(names[i] for i in res.path)
        ok = replay_visible(v, word, max_steps=len(word) + 1) == tuple(root)
        rows.append({"v": list(v), "found": True, "replayed": ok, "length": len(word)})
    lengths = [row["length"] for row in rows if row.get("replayed")]
    return {
        "graph": f"m{m}r{r}",
        "T": budget(m, r),
        "beam_width": width,
        "starts": len(rows),
        "solved_and_replayed": len(lengths),
        "replay_failures": sum(
            1 for row in rows if row.get("found") and not row["replayed"]
        ),
        "max_length": max(lengths, default=None),
        "mean_length": round(sum(lengths) / len(lengths), 2) if lengths else None,
        "over_T": sum(1 for x in lengths if x > budget(m, r)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", nargs="*", default=[])
    parser.add_argument("--beam", action="store_true")
    parser.add_argument("--beam-width", type=int, default=2000)
    parser.add_argument("--max-starts", type=int, default=40)
    parser.add_argument("--out")
    args = parser.parse_args()
    registry, _, table_dir = paths()
    reg = load_registry(registry)
    report = {
        "cayleypy_version": getattr(cayleypy, "__version__", "unknown"),
        "bfs": [],
        "beam": [],
    }
    for g in reg["graphs"]:
        if g.get("table") and f"m{g['m']}r{g['r']}" not in args.skip:
            row = check_bfs(g, table_dir)
            print(json.dumps(row), flush=True)
            report["bfs"].append(row)
    if args.beam:
        for g in reg["graphs"]:
            if not g.get("table"):
                row = beam_words(g, args.beam_width, args.max_starts)
                print(json.dumps(row), flush=True)
                report["beam"].append(row)
    report["bfs_all_equal"] = all(r["layer_sizes_equal"] for r in report["bfs"])
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            raise FileExistsError(out)
        out.write_text(json.dumps(report, indent=2) + "\n")
    return (
        0
        if report["bfs_all_equal"]
        and not any(b["replay_failures"] for b in report["beam"])
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
