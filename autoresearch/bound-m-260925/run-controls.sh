#!/usr/bin/env bash
# Controls on the frozen sets (trusted repository code; no provider). Writes controls/ (fresh paths only).
# (a) naive and (b16) sweep-16 run as candidates under Seatbelt on development and edge; on the holdout they
# run with --holdout --no-os-sandbox (trusted bound_control_*.py only). (b) sweep-LP runs in-process (trusted).
# (c) the sort-m9 GEPA finalist runs only under Seatbelt (development). Holdout controls do not consume the
# one-shot holdout, which is reserved for frozen engine finalists.
set -euo pipefail
cd "$(dirname "$0")/../.."
D=autoresearch/bound-m-260925
F=$D/frozen
O=$D/controls
mkdir -p $O
for set in development edge; do
  python -m integrations.bound_evaluator --program integrations/bound_control_naive.py --families $F/$set.json --output $O/a-naive-$set.json
  python -m integrations.bound_evaluator --program integrations/bound_control_sweep.py --families $F/$set.json --output $O/b16-sweep16-$set.json
  python -m integrations.bound_control_sweeplp --families $F/$set.json --output $O/b-sweeplp-$set.json
done
python -m integrations.bound_evaluator --holdout --no-os-sandbox --program integrations/bound_control_naive.py --families $F/holdout.json --output $O/a-naive-holdout.json
python -m integrations.bound_evaluator --holdout --no-os-sandbox --program integrations/bound_control_sweep.py --families $F/holdout.json --output $O/b16-sweep16-holdout.json
python -m integrations.bound_control_sweeplp --holdout --families $F/holdout.json --output $O/b-sweeplp-holdout.json
python -m integrations.bound_control_sortprog --families $F/development.json --out-dir $O --output $O/c-sortprog-development.json
python -m integrations.bound_audit --families $F/development.json $F/holdout.json $F/edge.json --results $O/*-*.json --output $O/audit.json
