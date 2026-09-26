#!/bin/sh
# capped exact probes at the seed-pool multipliers (reach report only)
cd "$(dirname "$0")/.."
while pgrep -f "midband_colgen.py 11 5" >/dev/null; do sleep 15; done
P="python3 midband_driver.py"
$P 12 5 3 4 0 --bound 307 --classes '12,11,10,9|8,7,6,5|4,3,2,1' --cap 10000000 > midband-runs/probe-m12-g5.log 2>&1
$P 13 6 3 7 0 --bound 386 --classes '13,12,11,10,9,8|7,6,5,4,3|2,1' --cap 10000000 > midband-runs/probe-m13-g6.log 2>&1
$P 13 7 3 7 0 --bound 386 --classes '13,12,11,10,9,8|7,6,5,4,3|2,1' --cap 10000000 > midband-runs/probe-m13-g7.log 2>&1
$P 14 7 7 25 1 --bound 1138 --classes '14,13,12,11,10,9,8|7,6,5,4,3,2|1' --cap 10000000 > midband-runs/probe-m14-g7.log 2>&1
$P 14 8 1 3 0 --bound 154 --classes '14,13,12,11,10,9,8|7,6,5,4,3,2|1' --cap 10000000 > midband-runs/probe-m14-g8.log 2>&1
$P 14 9 1 3 0 --bound 154 --classes '14,13,12,11,10,9,8|7,6,5,4,3,2|1' --cap 10000000 > midband-runs/probe-m14-g9.log 2>&1
