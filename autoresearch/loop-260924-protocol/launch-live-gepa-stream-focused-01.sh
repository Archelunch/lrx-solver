#!/usr/bin/env bash
# Reviewed development-only campaign. Do not run until payload approval is recorded.
set -euo pipefail
umask 077

project_dir="/Users/pavluhin/Documents/Projects/lrx-lab"
campaign_dir="$project_dir/autoresearch/loop-260924-protocol"
frozen_dir="$campaign_dir/frozen"
run_dir="$campaign_dir/gepa-live-stream-focused-01"
ledger_path="$campaign_dir/broker-ledger-stream-focused-01.json"
broker_log="$campaign_dir/broker-stream-focused-01.log"

if [[ -z "${XAI_API_KEY:-}" ]]; then
  echo "XAI_API_KEY must be supplied through the environment" >&2
  exit 1
fi
if [[ -e "$run_dir" || -e "$ledger_path" || -e "$broker_log" ]]; then
  echo "Fresh GEPA run, ledger, or broker log path already exists" >&2
  exit 1
fi
cd "$project_dir"
budget_remaining="$(python - <<'BUDGET'
from decimal import Decimal
import json
from pathlib import Path
root = Path('autoresearch/loop-260924-protocol')
paths = (root/'broker-ledger.json', root/'broker-ledger-recovery-01.json',
         root/'chat-latency-probe-01'/'ledger.json',
         root/'broker-ledger-stream-01.json')
states = [json.loads(path.read_text()) for path in paths]
if [len(state['attempts']) for state in states] != [1, 1, 1, 1]:
    raise SystemExit('prior campaign ledger attempts changed')
remaining = Decimal('5') - sum(Decimal(str(state['spent_usd'])) for state in states)
if remaining <= 0:
    raise SystemExit('campaign budget exhausted')
print(remaining)
BUDGET
)"

python -m integrations.research_budget serve \
  --upstream-url https://api.x.ai/v1 --model grok-4.7 \
  --ledger "$ledger_path" --max-requests 1 --max-usd "$budget_remaining" \
  --input-usd-per-million 2.2 --output-usd-per-million 6.6 \
  --port 8877 --max-tokens 4096 --reasoning-reserve 20000 \
  --timeout 600 --upstream-stream > "$broker_log" 2>&1 &
broker_pid=$!
trap 'kill "$broker_pid" 2>/dev/null || true; wait "$broker_pid" 2>/dev/null || true' EXIT

python - <<'PY'
import time
from urllib.request import urlopen
for _ in range(50):
    try:
        with urlopen("http://127.0.0.1:8877/health", timeout=1) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(0.1)
else:
    raise SystemExit("local research broker did not become ready")
PY

python -m integrations.official_backends run \
  --engine gepa --seed "$frozen_dir/allcuts_seed.py" \
  --cases "$frozen_dir/development.json" \
  --baseline "$frozen_dir/development-baseline.json" \
  --incumbent "$frozen_dir/development-incumbent.json" \
  --dual "$frozen_dir/development-dual.json" \
  --run-dir "$run_dir" --python "$project_dir/.venv-official/bin/python" \
  --broker-url http://127.0.0.1:8877/v1 --model grok-4.7 \
  --iterations 1 --max-tokens 4096 --reasoning-effort low --focused-reflection \
  --llm-timeout 610 --wall-seconds 1200 --max-evals 64 \
  --archive "$campaign_dir/development-archive.sqlite" \
  --archive-query k5-mask302-order15713 --archive-limit 1 \
  --research-context "$campaign_dir/development-context.txt"
