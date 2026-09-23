# LRX Lab

Instructions for coding agents working in this repository.
Read `research/problem.md`, `research/claims.md`, and `ROADMAP.md` first.

- Minimize implementation size. The runtime is the Python standard library;
  numpy is an optional extra used only by the `lift` command.
- Treat the main conjecture as open. Attribute manuscript results explicitly.
- Finite tests validate finite cases. Word replay certifies an upper bound only.
- Infinity means no admissible path after a complete exact computation.
  Resource limits mean INCOMPLETE and must never become infinity.
- The canonical visible sorting radius is not a distinguished-root radius.
- Candidates may change constrained JSON policies, not evaluator code or data.
- The autoresearch orchestrator may modify search-side
  code (src/lrx/evolve.py, proposers.py, prompt.py, feedback.py, trace.py,
  report.py, integrations/, new tests/test_search_*.py) to improve the search.
  The trusted core listed in tools/orchestrator.py (TRUSTED) is locked by
  autoresearch/trusted.lock.json; only a human re-locks it after review.
- Never execute generated code. Credentials stay in environment variables.
- Live API calls, new dependencies, remote writes, and long campaigns require
  explicit authorization. Use mock HTTP tests by default.
- Preserve existing run files; use fresh paths for new evidence.

Verify changes from this directory:

    python -m unittest discover -s tests -p 'test_*.py' -v
    python -m compileall -q src tests
    python -m src.lrx.cli smoke

Report actual command output and limitations. Do not write optimistic completion
reports while tests fail or features are stubs.
