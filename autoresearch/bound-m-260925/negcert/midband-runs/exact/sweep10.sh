#!/bin/sh
cd "$(dirname "$0")/../.."
for g in 4 6 3 7 2 8 1 9; do
  python3 midband_colgen.py 10 $g --mode exact --seeds midband-runs/pool-seeds.json --out midband-runs/exact --budget 1500 --cap 15000000 > midband-runs/exact/colgen-m10-g$g.log 2>&1
done
