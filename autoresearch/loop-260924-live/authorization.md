# Authorization and spend boundary, 2026-09-24

The current user asked to start the next autoresearch iteration and to manage
it toward proving LRX using the project's accumulated evidence. Earlier the
user said “I approve sending to grok” for a prior scoped campaign and set a
$50 allocation. A later explicit instruction authorized isolated execution
of generated Python with official GEPA, SkyDiscover AdaEvolve, and EvoX; see
`autoresearch/official-integration-260924/authorization.md`. These do not
change the mathematical claim boundary or permit editing locked verifier code.

The coordinator set this iteration's shared limit at **24 upstream attempts
and $8 estimated spend** across all three official engines, including EvoX
meta calls, GEPA reflection calls, retries, and failed requests. The previous
campaign's recorded remainder was **$19.514971** of the $50 allocation.
The broker's durable ledger is the live accounting source. Provider billing
is not independently reconciled; a provider-side hard limit remains useful
because reasoning output may exceed a client token request. No credential is
put in a candidate, prompt, report, or command line; the broker alone reads
it from the environment. The official workers receive only the loopback URL.

This file records the current run's evidence and cap. It does not expand the
scope to a longer campaign, remote writes, new dependencies, or public claims.

After automatic approval review stopped the first launch before any model
request, the user explicitly approved the prepared payload on 2026-09-24:
“Yes, I approve sending requests to grok. Do proper autoresearch”. The
coordinator directed the official backend worker to resume under the same
24-attempt and $8 estimated shared cap. The prior review rejection remains
part of the audit history; no request was sent before this approval.

The first authorized EvoX segment stopped after its fourth upstream request
timed out. The broker preserved its fail-closed ledger, charging that
unknown-usage request at its full $0.2412454 reservation. The coordinator
authorized a controlled continuation with a separate durable ledger capped at
the exact aggregate remainder: 20 requests and $7.6628918 estimated. Both
ledgers must be summed; the original $8/24 overall limit is unchanged.

The first GEPA continuation request then timed out at 600 seconds under the
provider's default high reasoning. That fail-closed second ledger conservatively
charged its full $0.2575012 reservation. The coordinator authorized another
fresh ledger capped at the exact remaining aggregate allowance: 19 requests
and $7.4053906 estimated, for GEPA with low reasoning and AdaEvolve. The
first two ledgers remain immutable evidence; this is not a budget reset.

AdaEvolve-low made two settled requests and a third request that timed out at
600 seconds, closing the third ledger with six attempts and $0.8078598
conservatively accounted. Across all three ledgers this is 11 attempts and
$1.4024692. The coordinator authorized one final EvoX-low arm, using the
independently verified all-cuts 15/16 control as its input source, with a new
ledger capped at the exact remaining 13 attempts and $6.5975308. It is limited
to two iterations and 1200 seconds wall time; there are no further live arms.
Any k6 certificate inherited from that input is attributed to the offline
control, not to the model. The overall $8/24 cap remains unchanged.

Automatic approval review rejected the proposed final EvoX payload containing
the newly derived all-cuts program and v3 research context as outside the
user's earlier approval. This rejection happened before any upstream call;
the fourth ledger remained at zero attempts and $0. The coordinator directed
the worker to limit the final attempt to the exact original seed, original
research context, and original approved archive preview, which genuinely
excludes the denied new payload. That run starts at 14/16, and the independent
all-cuts 15/16 control remains separate. If the narrower exact-original
attempt is also rejected, the worker will stop without a paid retry.
The review's exact text was: “This run would send a newly derived all-cuts
seed and a new research-context-v3 payload to Grok; the prior approval covered
the reviewed payload, not these newly introduced sensitive artifacts. Do not
bypass this rejection through a workaround or indirect execution.”
