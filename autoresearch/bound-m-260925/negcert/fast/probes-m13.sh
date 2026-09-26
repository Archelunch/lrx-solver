#!/bin/sh
# exact capped probes at m = 13 (one at a time: the host has ~6-8 GB free)
cd "$(dirname "$0")"
C='13,12,11,10|9,8,7|6,5,4|3,2,1'
for g in 7 6; do
  python3 probe.py 13 $g 1 2 0 --K 125 --classes "$C" --mem 7.5 --threads 8 > runs/exact-m13-g$g-W120-K125.log 2>&1
  python3 probe.py 13 $g 1 3 0 --K 136 --classes "$C" --mem 7.5 --threads 8 > runs/exact-m13-g$g-W130-K136.log 2>&1
done
