# Track 3 install log (2026-09-25)

Authorized for this track: elan plus the pinned Lean toolchain in the user's home,
not the repository. No Batteries, no Mathlib, no comparator.

## Commands (actual)

```
curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o elan-init.sh
  sha256 a620ff1641616222c8d37c54845492004bb84d6877cdbc944dd65c1aa685bf53
sh elan-init.sh -y --default-toolchain none --no-modify-path     # no shell profile edits
~/.elan/bin/elan toolchain install leanprover/lean4:v4.34.0      # 22 s wall (16:06:50-16:07:14 CEST)
cd autoresearch/lean-loop-260925/lrxlean && PATH=<toolchain>/bin:/usr/bin:/bin lake build   # 10 s
```

## Identity and sizes (measured)

| Item | Value |
|---|---|
| elan | `elan 4.2.4 (227caca13 2026-08-25)`, `no active toolchain` (no default set) |
| lean | `Lean (version 4.34.0, arm64-apple-darwin24.6.0, commit 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b, Release)` |
| lake | `Lake version 5.0.0-src+293d5d0 (Lean version 4.34.0)` |
| leanchecker | ships in the toolchain `bin/` (also cadical, leanc, leanir, leantar, clang, ld64.lld) |
| `du -sh ~/.elan` | 2.7G (toolchain 2.7G) |
| `lrxlean/.lake` | 100M (gitignored by the repo's `build/` rule) |
| disk after | 46Gi free of 460Gi (89% used) |

`lean --help` flag names used by the evaluator: `--json`, `-o`, `-j/--threads`, `-M/--memory` (MB),
`-D name=value`. Also present: `-T/--timeout` (allocation count), `--plugin`, `--load-dynlib`
(never passed).

## Observations

- `leanchecker` calls `findSysroot`, i.e. runs `lean --print-prefix`; stage B therefore needs
  `process-fork` and exec of `bin/lean`. `leanchecker --help` is not a help flag: it is treated as
  a flag and the tool checks the current module set (it ran for minutes and was killed).
- `leanchecker Cand`: 2 s. `leanchecker --fresh Cand` on the L1 control: 36-40 s.
- `lean` resolves its own path, so the Seatbelt profile grants `file-read-metadata` on the literal
  ancestor directories of the toolchain, build and scratch paths (no contents). No `mach-lookup`,
  no network and no fork are needed for stage A.
- Lean does not write the olean when the file has any error (return code 1). The evaluator
  therefore blanks failing top-level blocks and re-elaborates (at most 3 passes).
- `native_decide` in v4.34 adds an auxiliary axiom `<decl>._native.native_decide.ax_1_1`; the audit
  reports it as a disallowed axiom.
- A rebuild of a copy of the project in another directory reproduced the Defs.olean and lrxaudit
  sha256 values in `lean.lock.json`.

## Uninstall

`~/.elan/bin/elan self uninstall` (removes ~/.elan), then `rm -rf autoresearch/lean-loop-260925/lrxlean/.lake`.
