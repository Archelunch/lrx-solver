"""Build holdout distance tables with src/lrx/table_bfs.build_table (unmodified).

Output: datasets/generated/sort-m9-260925/ (git-ignored, fresh path).
Each table runs in its own process group with a wall-clock limit; a timeout is
recorded as INCOMPLETE in build_log.jsonl and never as a table.
Usage: python autoresearch/sort-m9-260925/build_tables.py 10,3:2400 9,6:3600
"""
import json, os, signal, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "datasets/generated/sort-m9-260925"
LOG = Path(__file__).with_name("build_log.jsonl")

CHILD = r'''
import json, sys, time
sys.path.insert(0, %r)
from src.lrx.table_bfs import build_table, write_table
m, r = %d, %d
t0 = time.time()
dist, meta = build_table(m, r, workers=10, max_bytes=12 * 1024**3)
meta = write_table(%r, m, r, dist, meta)
row = {k: meta[k] for k in ("m","r","n","states","reached","complete","radius","seconds","table_sha256","layer_sizes")}
row["wall_seconds_incl_write"] = round(time.time() - t0, 2)
row["T_m(n)"] = m*(m+1)//2 + (r-1)*(m-2)
print(json.dumps(row), flush=True)
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        mr, limit = arg.split(":")
        m, r = map(int, mr.split(","))
        t0 = time.time()
        proc = subprocess.Popen(["nice", "-n", "5", sys.executable, "-c", CHILD % (str(ROOT), m, r, str(OUT))],
                                stdout=subprocess.PIPE, text=True, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=int(limit))
            row = json.loads(out.strip().splitlines()[-1]) if proc.returncode == 0 else {"m": m, "r": r, "status": "FAILED", "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            row = {"m": m, "r": r, "status": "INCOMPLETE", "reason": f"wall limit {limit}s exceeded"}
        row["driver_wall_seconds"] = round(time.time() - t0, 1)
        with LOG.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
