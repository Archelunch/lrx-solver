# corr-cert task: universal coefficients for the Theorem 3 correlation certificate

Date 2026-09-24. Goal: make GEPA, AdaEvolve, EvoX and a sequential control
evolve a *coefficient program* `coefficients(m) -> dict` that emits a
Theorem 3 certificate (`THEOREM.md`) passing the exact stdlib checker
`corrcert.py` for every development m, ideally by a single formula uniform
in m. Optimizers find the program; they do not prove anything. A separate
worker in this same directory ("corr-cert") is running a deterministic LP
ansatz fit (`search_lp.py`, `ansatz_lp.py`, `certs*/`, `patterns.py`); this
scaffold is additive engine plumbing and does not touch any of that worker's
files, `corrcert.py`, `THEOREM.md`, `PROTOCOL.md`, `FIT-SPEC.md`, or
`PATTERNS.md`.

## Candidate

A Python program (executed only under the existing Seatbelt sandbox, the
same mechanism `integrations/lift_evaluator.py` uses, via
`integrations/program_sandbox.py` / `integrations/program_evaluator.py`
unchanged) exposing `coefficients(m: int) -> dict`.

corrcert.py's own cert dict uses Python tuple keys ((a, b) for `lambda`,
(a, b, c) for `alpha`/`beta`/`gamma`) and a bare int key for `mu`, none of
which are valid JSON object keys, and a candidate only ever returns
JSON-safe data across the sandbox boundary. So `coefficients(m)` must return
the *encoded* form (see `integrations/corr_task.py`, `encode_cert` /
`decode_cert`):

```json
{"m": 9, "Q": 1000000,
 "lambda": {"0,1": -3821, "0,2": 44, "...": "..."},
 "mu": {"0": [12, -4, "...", 0], "1": ["...(m-1 ints)"], "...": "..."},
 "alpha": {"0,1,2": ["...(m-1 ints)"], "...": "..."},
 "beta":  {"0,1,2": ["...(m-1 ints)"], "...": "..."},
 "gamma": {"0,1,2": ["...(m-1 ints)"], "...": "..."}}
```

Keys are comma-joined decimal integers with no spaces: `"a,b"` for each pair
`a < b` (so `set(lambda) == set(pairs(m))` after decoding), `"a"` for each
`0 <= a < m` in `mu`, and `"a,b,c"` for each triple `a < b < c` in
`alpha`/`beta`/`gamma`. Every `mu[a]` and every triple list has exactly
`m - 1` entries, indexed `q = 1..m-1` in order. All values must be exact
Python `int`s (no floats, no strings-as-numbers); `Q` must be a positive
int. `integrations/corr_task.decode_cert(m, raw)` converts this into
corrcert.py's dict-of-tuples form, raising `ValueError` on any shape
mismatch -- a malformed certificate is never repaired, it is scored as
invalid output (see Score, below).

Constraints: stdlib only, source at most 64 KiB, wall limit 10 seconds per
`m`. Do not read files, the network, or environment variables (the worker
runs under `program_sandbox.sandbox_profile`, which denies all of that by
default; the constraint is stated in the system prompt for the model's
benefit, not relied on as the only enforcement).

## Score (per candidate, over the frozen development set)

For each `m` in the development set, `integrations/corr_evaluator.py`:

1. Runs `coefficients(m)` in the sandbox (`corr_worker.py`, the same
   untrusted-JSON-bridge pattern as `lift_worker.py`).
2. Decodes the JSON-safe output with `corr_task.decode_cert(m, ...)`.
3. Calls `corrcert.check_certificate(m, cert)` exactly (stdlib `Fraction`
   arithmetic; the checker is never modified).
4. `passed` iff `ok == True` and `epsilon < 1` (i.e. `res["proves"]`).
5. If not passed but the output was valid and well-formed: `magnitude` =
   sum of `-slack` over every violated (5)/(6) check (`slack < 0` entries
   from `check_certificate`, called with `max_violations` large enough that
   nothing is truncated for m <= 20) plus `max(0, epsilon - 1)`.
6. If the run crashed, timed out, or the output was invalid/malformed:
   `magnitude = INVALID_GAP = 5000` (a fixed, undocumented-in-corrcert
   penalty constant chosen here, analogous to lift's `INVALID_GAP = 4000`;
   see `integrations/corr_evaluator.py`). This is never partial credit and
   is never repaired.

`combined_score = passes + 0.5 / (1 + violation_sum)`, where `passes` is
the count of development `m` that passed and `violation_sum` is the sum of
`magnitude` over every `m` that did not pass. This is a direct
implementation of the formula given in this task's brief. It differs from
`lift_evaluator`'s `combined_score = certificates + 0.5*valid/N +
0.5/(1+gap_sum/N)` because the lift task has many *instances* per candidate
(one certificate opportunity per parent-family insertion) whereas this task
has exactly one certificate opportunity per `m` -- there is no separate
"valid/N" term because "valid" and "passed" would otherwise coincide for a
well-formed-but-failing candidate, and there is no `/N` normalization on
`violation_sum` because the group's own numeric epsilons already shrink
with `m` (see `THEOREM.md`'s table), so an un-normalized sum keeps the
penalty comparable to `passes` without a magic per-m weighting choice.

`combined_score` is a search signal only. A candidate that passes every
development `m` is not a proof for any `m` outside the frozen set, let
alone a proof of the general conjecture; see `THEOREM.md` and
`PROTOCOL.md`'s success levels.

## Feedback packet (development only, <= 2000 characters)

`integrations/corr_backends.packet()` builds `CORR_PACKET_V1` text: overall
`passes`/N and `violation_sum`, then for each failing `m` up to 3 of its
worst violated constraints (kind, indices, `q`, `t`, `slack`), the `kappa`
value at `q` for pair violations (`corrcert.kappa(m, a, b, q)`), the
`epsilon` for that `m`, and this reminder verbatim:

> LP optimum is 0 for every m; E=0 only at the reversal orders p_i = -i mod
> m; forced tight rows at q = m-(b-a) and triple rows at (m-(b-a),
> m-(c-b)); linear potentials alpha=xq+c1, beta=xt+c2, gamma=-xs+c3 satisfy
> (5) iff c1+c2+c3<=0 and c1+c2+c3+xm<=0.

## Proposer context: worked examples and residual facts (2026-09-24 update)

Added to `integrations/corr_backends.SYSTEM` (and recaptured into
`first-prompt.md`) after the deterministic ansatz control (step 4,
`REPORT.md`) failed to find a universal formula. Kept under 6 KB total; see
`corr_backends.WORKED_EXAMPLES` and `corr_backends.RESIDUAL_FACTS` for the
exact text sent to the model.

**Worked examples.** The two known exact `epsilon = 0` certificates, from
`certs-exact/m4.json` and `certs-exact/m5.json`, printed compactly:
- m=4, Q=1: `lambda` (0,1)=12 (0,2)=4 (0,3)=0 (1,2)=-24 (1,3)=-12 (2,3)=-20;
  `mu_0`=[-8,-4,0] `mu_1`=[-4,0,4] `mu_2`=[4,0,-4] `mu_3`=[0,-4,-8]; every
  `alpha`/`beta`/`gamma` is 0 (no triple terms needed at m=4).
- m=5, Q=1: `lambda` (0,1)=25 (0,2)=20 (0,3)=15 (0,4)=0 (1,2)=-15 (1,3)=0
  (1,4)=-5 (2,3)=-35 (2,4)=-20 (3,4)=-35; `mu_0`=[-14,-18,3,4]
  `mu_1`=[-17,-9,-16,2] `mu_2`=[-10,0,0,-10] `mu_3`=[2,-16,-9,-17]
  `mu_4`=[4,3,-18,-14]; 16 nonzero triple coefficients, all +-5, each a
  width-2 run of consecutive q: (0,1,2) alpha=[0,-5,-5,0] beta=[0,0,0,5]
  gamma=[0,0,-5,0]; (0,1,4) alpha=[-5,-5,0,0] beta=[0,0,0,-5]
  gamma=[0,0,5,0]; (0,3,4) alpha=[0,0,0,-5] beta=[-5,-5,0,0] gamma=[0,0,5,0];
  (2,3,4) alpha=[0,0,0,5] beta=[0,-5,-5,0] gamma=[0,0,-5,0].

**What is known to fail** (from the ansatz control, `REPORT.md` step 4, not
prescriptive): degree<=3 polynomials in (a,b,c,m) plus step/indicator terms
at the kappa thresholds, and q times those steps, fit m=4..8 exactly but
failed at the first untried m=9 (about 1200 violated rows). The bottleneck
is triples with a unit gap (b-a==1 or c-b==1); freeing only those triples'
coefficients from the polynomial made the fit exact through m=10. In the
infeasibility structure, about 60% of the violation mass sits on wrapping
rows (q+t>m) and about a third at the equality-order row q=m-(b-a); the
heaviest gap classes are (b-a,c-b) in {(1,1),(1,2),(2,1),(1,3)}. Possible
directions, not prescribed: dependence on min/max of the gaps, floor/mod
expressions, or piecewise definitions with breakpoints tied to both q and
m-q. Every known epsilon=0 certificate is tight at the reversal-order rows
q=m-(b-a) and (m-(b-a), m-(c-b)).

**Algorithmic constructions are allowed.** `coefficients(m)` may compute its
output algorithmically for the given m -- loops, or a small exact linear
solve restricted to the known-tight rows, are fine -- as long as it stays
standard-library and finishes within 10 s per m. A construction with a
human-checkable argument for why it holds for every m is worth more than a
per-m lookup table; the holdout set (m=13..20) tests m the program has
never seen.

**Packet update.** `corr_backends.packet()` now annotates each of the 3
worst violations per failing m with wrap/nonwrap (`q+t>m` vs `q+t<m`) for
triple rows and the gap class (`b-a`, and `c-b` for triples).

## Development / holdout sets

Development: `m = 4..12`, frozen at
`autoresearch/corr-cert-260924/frozen/development.json`
(`{"schema": "lrx-corrcert-m-set-v1", "set": "development", "m_values": [4..12]}`).
Holdout: `m = 13..20`, frozen the same way at `frozen/holdout.json`, never
loaded by any engine, proposer, sequential control, or smoke
(`corr_task.guard_not_holdout`, mirroring lift's `_verify_inputs` guard, and
`corr_backends._verify_inputs`, which additionally refuses to run unless the
loaded development file's sha256 matches `frozen/manifest.json`). Both files
and their sha256 are recorded in `frozen/manifest.json`. Holdout is
evaluated at most once, by a human-run offline check after any finalist is
frozen -- never automatically.

## Evaluation cost note (no staging/screening, unlike lift)

`corrcert.expected_checks(m) = C(m,3)*(m-1)*(m-2) + C(m,2)*(m-1)`: 42 checks
at m=4, ~24,926 at m=12 (~176,000 across the whole development set). A full
9-m development evaluation of the seed program measured **0.14 seconds**
end to end under the macOS Seatbelt sandbox (see below), so unlike the lift
task there is no parent-screening stage: every candidate gets one full
development evaluation, every time.

## Seed program: the F1 linear-potential family

`integrations/corr_control_f1.py` (path referenced as `"seed"` in
`campaign-config.json`) implements FIT-SPEC.md's F1 family literally: triple
functions identically zero (the `x=0, c1=c2=c3=0` point of the linear
family in `THEOREM.md`'s structural note, which always satisfies (5) with
equality `0 <= 0`), `lambda_ab = 0`, and `mu_a(q) = MULT * (q - (m-1-a))`
for every `a` (`MULT = 4`), generalizing `THEOREM.md`'s exact m=4
certificate (`mu_0 = 4(q-3)`, `mu_1 = 4(q-2)`, `mu_2 = -4(q-2)`,
`mu_3 = -4(q-1)` at Q=1) by one formula applied to every index, not only the
reversal-symmetric half that the m=4 example actually uses. This is an
honest first guess, not a fit: `FIT-SPEC.md` states no closed form is
established, and `PATTERNS.md` records that `mu_a(q)` is not linear in `q`
for `m >= 5`.

**Real measured score (macOS Seatbelt sandbox, `corr_evaluator.evaluate`,
development set m=4..12), not fabricated:**

```
passes: 0 / 9
violation_sum: 233998
combined_score: 2.136761268210548e-06
seconds: 0.14
```

Per-m detail (`epsilon`, violation magnitude):

| m | epsilon | magnitude |
|---|---|---|
| 4 | -22 | 264 |
| 5 | -48 | 908 |
| 6 | -90 | 2452 |
| 7 | -152 | 5580 |
| 8 | -238 | 11368 |
| 9 | -352 | 21160 |
| 10 | -498 | 36752 |
| 11 | -680 | 60438 |
| 12 | -902 | 95076 |

It **fails m=4**, contrary to what a naive reading of "generalizes the exact
m=4 certificate" might suggest -- the naive same-formula-for-every-a
generalization does not actually reduce to the group's m=4 certificate for
`a >= ceil(m/2)` (that certificate uses the *reversal-symmetric* map
`mu_{m-1-a}(q) = mu_a(m-q)`, not the same closed form applied directly to
every index). This is reported as-is; the seed was not hand-tuned to pass
anything.

## Campaign scaffold

- `campaign-config.json`: iterations gepa=60, sequential=60, adaevolve=50,
  evox=40; `llm_timeout` = broker timeout + 30 s, computed at run time from
  `broker-config.json` (not stored twice). No development-archive database
  is set up here (unlike lift's `development-archive.sqlite`) -- deliberately
  omitted as out of scope; `corr_backends.CorrVerifier` still writes every
  evaluation artifact under `<run_dir>/verified/evaluations/`, which is
  enough replay evidence for this task's much smaller search space.
- `broker-config.json`: copied from `autoresearch/lift-m9-260924/broker-config.json`
  (same model/pricing/reasoning fields), with a fresh ledger path
  (`broker-ledger-corr.json`, must not exist before first live use) and
  `max_usd: 25`. `max_requests` recomputed from the existing reservation
  formula at the new cap: `min(floor(25 / 0.1497408), 400) = 166`.
- `run-gepa.sh` / `run-sequential.sh` / `run-adaevolve.sh` / `run-evox.sh`:
  same guarded pattern as the lift ones (`check-approval` then
  `exec ... live --engine X`); **no `payload-approved.sha256` exists in this
  directory**, so none of these scripts can currently run -- that file is
  created only after explicit human approval, per `AGENTS.md`.
- `mock_api.py`: offline OpenAI-compatible responder for smokes, modeled on
  `autoresearch/lift-m9-260924/mock_api.py`. Its only knob is the seed's
  `MULT` constant; every proposal it returns is a real, syntactically valid
  `coefficients(m)` program (still failing the certificate -- this exercises
  the search mechanism, not a search for a real fix).
- `smoke-gepa/`, `smoke-sequential/`, `smoke-adaevolve/`, `smoke-evox/`: real
  offline runs (mock HTTP broker on localhost, no provider call) of all four
  arms via `integrations/corr_backends.py run` / `sequential`, using the
  pinned `.venv-official` interpreter (gepa==0.1.4,
  skydiscover==0.2.0@0d932b6...). All four completed with `status: COMPLETE`;
  none produced a certificate (expected -- the mock only varies `MULT`).
  `smoke-gepa-capture/` holds the raw captured GEPA reflection requests used
  to build `first-prompt.md`.
- `first-prompt.md` / `first-prompt.sha256`: the real, captured first GEPA
  reflection prompt (`messages` array) from the offline `smoke-gepa` run,
  written by `corr_backends.write_first_prompt`, exactly as lift's are.

## Budget and controls

No live call has been made under this scaffold. `broker-config.json` and
`campaign-config.json` are staged pending explicit human approval
(`payload-approved.sha256`, created only after review of
`corr_backends.approval_material`/`approval_hash`). Suggested order,
mirroring the lift campaign's user-approved plan: sequential control and
GEPA first, matched iteration counts (60); AdaEvolve and EvoX only after
GEPA shows one productive cycle. Kill conditions per `PROTOCOL.md`: no
program passing `m >= 10` after 150 proposals per arm, or the deterministic
LP-fit worker already passing holdout (in which case these engines are
skipped entirely).
