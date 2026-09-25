#!/bin/sh
# Feasibility table for step 4 (appends one JSON line per run to ansatz_table.log)
cd "$(dirname "$0")"
for spec in "$@"; do
  set -- $spec
  python3 ansatz_lp.py $1 4 $2 --deg $3 > ansatz/_last.out 2>&1
  tail -1 ansatz/_last.out >> ansatz_table.log
done
