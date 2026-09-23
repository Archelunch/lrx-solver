#!/bin/sh
# Launch the Claude autoresearch orchestrator for LRX campaigns.
#   tools/run_orchestrator.sh            interactive session (recommended first time)
#   tools/run_orchestrator.sh --headless non-interactive run, prints the final summary
# Restrictions come from autoresearch/orchestrator.settings.json (no edits to
# src/, tests/, datasets/; no push). Spend cap: LRX_MAX_TOTAL_USD (default 20).
set -e
cd "$(dirname "$0")/.."
ITER="${ITERATIONS:-6}"
BRIEF="${BRIEF:-autoresearch/PROGRAM.md}"
PROMPT="/autoresearch
Goal: Make progress toward a proof of the LRX sorting-radius conjecture (E_r(n) <= C(n,2)-(r-1)(r+4)/2 for m=n-r>=8) by improving and running the search system (GEPA/AdaEvolve engines, proposers, prompts, feedback, campaigns) and the exact finite checks that decide which proof routes are alive. Read autoresearch/PROGRAM.md and ${BRIEF} first and follow them. The conjecture stays open; findings are finite.
Scope: campaigns/**, candidates/leads/**, prompts/**, autoresearch/**, research/claims.md, src/lrx/evolve.py, src/lrx/proposers.py, src/lrx/prompt.py, src/lrx/feedback.py, src/lrx/trace.py, src/lrx/report.py, integrations/**, tests/test_search_*.py
Metric: proof-progress ratio of the best sound rules lead (max over m>=8 train graphs of max word / T; 1.0 = within the conjectured budget)
Direction: lower_is_better
Verify: python tools/orchestrator.py ratio
Guard: python tools/orchestrator.py trusted && python tools/orchestrator.py spend && python -m unittest discover -s tests -p 'test_*.py' -q
Iterations: ${ITER}
--evals"
if [ "$1" = "--headless" ]; then
  exec claude -p "$PROMPT" --settings autoresearch/orchestrator.settings.json --permission-mode acceptEdits
fi
exec claude --settings autoresearch/orchestrator.settings.json "$PROMPT"
