# Official framework program-search pilot

This is a separate, bounded experiment on m=8 residual block families. The
original JSON-policy campaigns and their results retain their old labels.
The user explicitly authorized isolated generated-code execution for this
task, overriding the older JSON-only rule in locked `AGENTS.md`; the scope is
recorded in `autoresearch/official-integration-260924/authorization.md`.
The main sorting-radius conjecture is open. A family certificate depends on
trusted word replay, reconstructed direct resource profiles, the direct
zero-block expansion bound, and exact rational mixture checking. A finite sample does not close
the full m=8 case.

## Frozen inputs and output boundary

`autoresearch/official-integration-260924/frozen/manifest.json` hashes the
source verification archive, the cycle 7 certificate list, older structural
datasets, and each new input. Its generator chooses 16 development and 8
confirmation cases, split evenly across 4–7 retained zero blocks. Every new
`(mask, order_index)` pair lies in the source projection residual and is absent
from those older datasets and cycle 7's 8,193 recorded cases. The direct
catalog baseline has a fixed 48-source pool and 4–7 retained profiles per
case; it is checked anew by the program evaluator before optimization.

The official engines receive only `development.json` and
`development-baseline.json`. A one-shot confirmation runs after engine selection,
using `confirmation.json` and `confirmation-baseline.json`, with no feedback
into proposer prompts. Generated candidates implement
`propose_words(case) -> list[str]`. The evaluator runs each program through a
bounded OS sandbox and builds all scores and certificates outside candidate
control. Source code, program output, and framework strategies are untrusted.

## Shared broker and archive

The local broker in `integrations/research_budget.py` fronts one configured
HTTPS chat provider. Both GEPA and SkyDiscover must use its loopback `/v1`
URL. It accepts text, one completion, a bounded `max_tokens`, and a narrow set
of chat fields. Every upstream attempt consumes a durable request slot,
including retries, errors, GEPA reflections, and EvoX meta calls. The broker
reserves estimated input, output, and reasoning cost before forwarding. It
halts after an upstream error, unknown usage, or a reservation overrun. A
ledger path has one live broker owner. `estimated_spent_usd` is
rate based and provider reported where available; it is **not an invoice hard
cap**, particularly if a provider exceeds a requested reasoning allowance.
Use a provider-side limit as an additional boundary. The upstream API key is
read from the broker environment and is never included in candidate context.

For an authorized paid pilot, start one broker for all arms with a fresh ledger:

```sh
python -m integrations.research_budget serve \
  --upstream-url https://api.x.ai/v1 --model grok-4.7 \
  --api-key-env XAI_API_KEY \
  --ledger autoresearch/official-integration-260924/live-budget.json \
  --max-requests 24 --max-usd 8 \
  --input-usd-per-million 2.2 --output-usd-per-million 6.6 \
  --max-tokens 4096 --port 8877
```

The broker remains a separate process. Its `http://127.0.0.1:8877/v1` endpoint
is the only URL given to official engines. A dummy local API key satisfies
client libraries; the real key remains in `XAI_API_KEY` in the broker process.
The staged $8 limit is a proposal for this pilot, not permission for other
campaigns. Preserve each ledger and use a new path for any separate run.

`integrations/research_archive.py` stores development evaluations in SQLite:
full candidate source, unified diff from a parent, score, feedback, raw
word/block traces, provenance, and a finite/invalid/incomplete claim status.
Confirmation writes are rejected. Search returns bounded full records:

```sh
python -m integrations.research_archive RUN/archive.sqlite "block 7" --limit 3
```

Search results are hypotheses and finite feedback, never proof by themselves.
The runner can stage up to `--archive-limit` selected development rows from
`--archive` into the next official proposer context. This was exercised in
`autoresearch/official-integration-260924/ada-archive-smoke-01/manifest.json`:
the recorded context hash and mock proposer request confirm that raw word/block
traces and source diff reached AdaEvolve. This is pre-run context selection;
there is no autonomous file-navigation or mid-run archive search tool.

## Run contract and validation

The official runner command is:

```sh
python -m integrations.official_backends run --engine gepa \
  --seed integrations/program_seed.py \
  --cases autoresearch/official-integration-260924/frozen/development.json \
  --baseline autoresearch/official-integration-260924/frozen/development-baseline.json \
  --run-dir /tmp/lrx-gepa-FRESH --broker-url http://127.0.0.1:8877/v1 \
  --iterations 2 --wall-seconds 600
```

Use `adaevolve` or `evox` for the other official engine choice. Always choose
a fresh run directory. The external environment pins GEPA 0.1.4 and
SkyDiscover 0.2.0 at commit `0d932b6`; neither is a dependency of the core
standard-library runtime. The runner and evaluator must verify the frozen
manifest and trusted-core lock before every run. The recorded result must
identify the exact upstream framework, candidate source hash, development
case hash, proposal count, reflection/meta-call count, broker attempts,
evaluation work, certificate scope, sandbox outcome, and any incomplete cases.

The [offline integration report](../autoresearch/official-integration-260924/report.md)
records actual GEPA, AdaEvolve and EvoX iterations, EvoX strategy execution,
broker mock HTTP accounting, archive retrieval with raw traces and diff, and
confirmation exclusion. Those smokes made no paid calls. A fresh one-shot
confirmation belongs after a separately authorized bounded comparison.
