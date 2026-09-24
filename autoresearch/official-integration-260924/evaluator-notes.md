# Executable-program evaluator boundary

The candidate interface is `propose_words(case) -> list[str]`. Each development
case supplies `m=8`, a permutation `labels`, retained nine-gap `mask`, `blocks`,
and an ID. The candidate may return up to 32 complete L/R/X sorting words per
case. It does not supply a cost, slope, or mixture weight.

`integrations.program_evaluator.evaluate(program_path, cases_path, output_dir,
baseline_path=...)` is the file adapter used by the official optimizers.
`ProgramEvaluator` is its in-memory form. It returns a numeric
`combined_score`, concise `feedback`, an evaluation artifact path, and a row
per family with raw and normalized words, rejection reasons, exact rational
weights, bounds, and execution status. `NO_CERTIFICATE` and `INCOMPLETE` never
mean infeasibility.

The parent snapshots at most 65,536 bytes of regular source and hashes those
bytes. It starts each case in a fresh process group and scratch directory with
a wall-time cap, CPU and file-size limits, bounded output, a scrubbed
environment, and a deny-by-default macOS Seatbelt profile. Only Python runtime
files and scratch are readable; only scratch is writable; network is denied.
The process group is killed even if the parent exits normally. Nested Seatbelt
is blocked by the Codex outer sandbox on this host, so the trusted coordinator
must be launched with the approved escalated host execution. There is no
automatic process-only fallback.

The trusted parent ignores candidate arithmetic. It removes invisible X on
two zeros and adjacent inverse rotations, replays every word against the
canonical visible root, and computes direct `base` and block slopes from
`resources()`. It literally expands and replays each component at unit and
nonunit lengths, then checks the exact `Fraction` mixture inequalities. Legacy
comparison baseline profiles are first reconstructed from their source word
and cut, materialized at unit lengths, and repriced as direct words. The
reviewed manuscript's comparison and stretching lemmas supply the
arbitrary-positive-length implication; finite literal replays are audits, not
an independent universal proof.

The frozen development diagnostic used 16 cases and the self-contained
`integrations/program_seed.py`: 14 family certificates, two beyond the frozen
direct baseline. This is an integration fixture, not a novelty or engine result.
`LRX_TEST_SANDBOX=1 python -m unittest tests.test_search_program_evaluator -v`
ran seven tests with no skips under approved escalated execution, including
attempted reads of project `.env` and confirmation JSON and an attempted write
to `program_evaluator.py`; the OS denied all three and the verifier hash stayed
unchanged. A separate literal stretch sweep replayed 384 expansions. The
source archive, other zero-block counts, and general sorting-radius conjecture
remain outside this evaluator's certified scope.

The completed offline native GEPA, AdaEvolve, and EvoX smoke exports all have
the same SHA-256 as the seed (`c27df808a5d2265c...`). For each engine, a
separate final-best audit reconstructed 43 direct support profiles, checked
the exact rational weighted base and slopes, and replayed 86 additional
nonunit literal expansions. Each has 14/16 development certificates, two
relative to this fixed baseline search, with score 2014.0. Identical seed
exports make this an integration check, not evidence of optimizer progress or
historical novelty. GEPA's earlier smoke predates the trusted-best-copy field;
its exported best hash still matches its verifier artifact and manifest.
