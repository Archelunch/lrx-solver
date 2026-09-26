#!/bin/sh
# column generation at m = 14, one instance at a time (host memory), 30 min budget each
cd "$(dirname "$0")"
while pgrep -f probes-m13.sh >/dev/null; do sleep 10; done
for g in 9 8 7; do
  python3 fast_colgen.py 14 $g --classes '14,13,12,11,10|9,8,7,6,5|4,3,2,1' --omega 3/1 --omega 3/2 --omega 1/1 --anytime \
    --wcap 40000000 --mem 7.5 --budget 1800 > runs/colgen-m14-g$g.log 2>&1
done
