"""Frozen post-search comparison on new states; never fed back to a proposer."""

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.lrx.candidates import Candidate, run_rules
from src.lrx.certificates import replay_visible
from src.lrx.dsl import budget


def main():
    directory = Path(__file__).parent
    output = directory / "confirmation-results.json"
    if output.exists():
        raise FileExistsError(output)
    data = (directory / "confirmation-states.json").read_bytes()
    manifest = json.loads((directory / "confirmation-manifest.json").read_text())
    assert hashlib.sha256(data).hexdigest() == manifest["sha256"]
    sources = [ROOT / "candidates/leads/49ab346cb44b2f1b.json"]
    sources.extend(Path(s) for s in sys.argv[1:])
    distinct = {}
    for source in sources:
        candidate = Candidate(json.loads(source.read_text()))
        distinct.setdefault(candidate.hash, (candidate, []))[1].append(str(source))
    # Record the complete finalist list before any confirmation result.
    (directory / "frozen-finalists.json").write_text(json.dumps(
        {h: paths for h, (_, paths) in distinct.items()}, indent=2) + "\n")
    results = []
    for key, (candidate, paths) in distinct.items():
        graphs = []
        for graph in json.loads(data):
            m, r = graph["m"], graph["r"]
            root = tuple(range(1, m + 1)) + (0,) * r
            lengths, failures = [], []
            started = time.perf_counter()
            for vector in graph["vectors"]:
                v = tuple(vector)
                word, reason = run_rules(candidate, v, m, r, 4 * (m + r) ** 2)
                if word is None:
                    failures.append({"v": vector, "reason": reason})
                else:
                    assert replay_visible(v, word, max_steps=len(word) + 1) == root
                    lengths.append(len(word))
            row = {"m": m, "r": r, "checked": len(graph["vectors"]),
                   "failures": len(failures), "failure_examples": failures[:3],
                   "max_word": max(lengths, default=None), "T": budget(m, r),
                   "mean_word": sum(lengths) / len(lengths) if lengths else None,
                   "seconds": time.perf_counter() - started}
            graphs.append(row)
        results.append({"hash": key, "sources": paths, "graphs": graphs})
        print(json.dumps({"hash": key, "failures": sum(g["failures"] for g in graphs),
                          "worst_ratio": max(g["max_word"] / g["T"] for g in graphs
                                             if g["max_word"] is not None)}), flush=True)
    output.write_text(json.dumps({"manifest": manifest, "results": results,
        "scope": "Finite random-state word replay; no universal bound or optimality claim."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
