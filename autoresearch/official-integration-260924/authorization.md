# Scope of the 2026-09-24 official integration

The user explicitly authorized this task to execute generated Python programs
for the official GEPA, SkyDiscover AdaEvolve, and EvoX integration. This is a
task-specific override of AGENTS.md's older JSON-only and no-generated-code
rules. The trusted core and `autoresearch/trusted.lock.json` remain unchanged;
only a human reviews and re-locks them. Candidate programs run through the
bounded OS sandbox of `integrations/program_evaluator.py`. Evolved strategy
code runs only inside the separate official framework worker sandbox. The
trusted evaluator and provider credential stay outside both.

The proposed paid pilot is limited to at most $8 total across all official
engines, including reflections and EvoX meta calls, with a shared request cap.
No paid call is authorized by this file itself; the parent task coordinates
any launch under the user's live-call authorization and records actual usage.
This file does not authorize remote writes, broader generated-code execution,
or modification of locked verifier files.
