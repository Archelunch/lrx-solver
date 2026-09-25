"""Build exact visible-state distance tables with src/lrx/table_bfs.build_table (unmodified).

Output directory: datasets/generated/outer-layer-260925/ (git-ignored).
Usage: python autoresearch/outer-layer-260925/build_tables.py m,r [m,r ...]
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.lrx.table_bfs import build_table, write_table  # noqa: E402

OUT = ROOT / "datasets/generated/outer-layer-260925"


def T(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def main():
    for arg in sys.argv[1:]:
        m, r = map(int, arg.split(","))
        t0 = time.time()
        dist, meta = build_table(m, r, workers=10, max_bytes=12 * 1024**3)
        meta = write_table(OUT, m, r, dist, meta)
        wall = time.time() - t0
        row = {k: meta[k] for k in ("m", "r", "n", "states", "reached", "complete", "radius", "seconds", "table_sha256")}
        row["wall_seconds_incl_write"] = round(wall, 2)
        row["T_m(n)"] = T(m, r)
        row["layer_sizes"] = meta["layer_sizes"]
        print(json.dumps(row), flush=True)
        del dist


if __name__ == "__main__":
    main()
