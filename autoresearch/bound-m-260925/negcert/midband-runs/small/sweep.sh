#!/bin/sh
# exact root LP by column generation, small m, every gap g
cd "$(dirname "$0")/../.."
for m in 5 6 7 8 9; do
  for g in $(seq 1 $((m-1))); do
    python3 midband_colgen.py $m $g --mode exact --out midband-runs/small --budget 900 > midband-runs/small/colgen-m$m-g$g.log 2>&1
  done
done
