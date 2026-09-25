# Track 3: Lean in the loop. Map and design spec (2026-09-25)

Status: design only. No install was done, no code changed, and no live
calls were made. `python tools/orchestrator.py trusted` reported
`{"ok": true, "changed": [], "missing_from_lock": []}` when this was written.
The Lean text below is **unchecked**. No Lean toolchain is installed, so
none of it has been elaborated yet. Phase 2 step 1 is to compile it.

Attribution: Lemma 1 (zero-stretch macros) and Lemma 4 (deletion of zero
atoms) belong to the research group
(`autoresearch/verify-m8-260924/package/LRX_MULTISET_M8_COMPLETE_THEOREM_RU.md`,
sections 3 and 6). This track would formalise statements of those lemmas. It
makes no priority claim, and nothing here bears on the open conjecture.

## 0. Machine and repository map (actual output)

```
which lean lake elan  -> lean not found / lake not found / elan not found
ls -d ~/.elan         -> No such file or directory
df -h ~               -> /dev/disk3s5 460Gi 353Gi 51Gi 88% (51 GiB free)
uname -m              -> arm64 ; sandbox-exec, clang, xcrun present ; brew at /opt/homebrew/bin
```

The repository has no Lean project: there is no `lakefile*` and no
`lean-toolchain`. The only `.lean` files come from the group:

| File | Imports | Content |
|---|---|---|
| verify-m8-260924/package/lean/MultisetBoundedBoxes.lean | Mathlib | scalar LP-dual / rounding inequalities (6 theorems, `#print axioms`) |
| verify-m8-260924/package/lean/MultisetOptimalBlock.lean | Mathlib | prefix-count / threshold arithmetic (7 theorems, omega/linarith) |
| downloads/.../cycle6/cloud-proof/MarkedZeroBudget.lean | Mathlib.Tactic.Linarith | abstract silent-block accounting |
| downloads/.../cycle6/cloud-proof/ProjectionFrontier.lean | Mathlib.Tactic.Linarith | conditional integer consequences |
| downloads/.../nine-gap/.../MultisetZeroFlux.lean | Mathlib | telescoping / slope inequalities |

Every one of these is a scalar lemma. Their own headers say that "the literal
LRX model and correctness of reference words are checked separately". So no
existing Lean file defines L, R, X, words or deletion, and Track 3 would be
the first formal model of LRX in this repository. The group's files depend on
Mathlib. Track 3 does not, which keeps the dependency small.

Upstream facts, checked on 2026-09-25 with read-only GitHub API calls. These
are not provider calls.

- Lean stable: v4.34.1, published 2026-09-24. v4.34.0 was published
  2026-09-14. v4.35.0-rc3 is a prerelease.
- Batteries, `leanprover/comparator` and `lean4export` each have a
  `v4.34.0` tag whose `lean-toolchain` is `leanprover/lean4:v4.34.0`.
  None of them has a v4.34.1 tag yet.
- `lean4checker` is archived. It ships as `leanchecker` in every toolchain
  from v4.28.0 onward.
- `comparator` needs `landrun`, which uses Linux Landlock. On macOS its repo
  offers only `scripts/fake-landrun.sh`, which is explicitly unsandboxed.
- Asset `lean-4.34.0-darwin_aarch64.tar.zst` is 561,666,156 bytes (the .zip
  is 796,889,666 bytes). elan v4.2.4 for aarch64-apple-darwin is 2.19 MB, and
  brew offers the formula `elan-init 4.2.4`.

## 1. Install plan (not executed; authorised dependency for this track only)

Pin: **`leanprover/lean4:v4.34.0`**. It is the newest stable release that
Batteries, comparator and lean4export are all tagged for. Moving to v4.34.1
buys nothing for this track.

```sh
# 1. elan (toolchain manager). Either:
brew install elan-init                      # formula elan-init 4.2.4
#    or, without brew (does not edit shell profiles):
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
  | sh -s -- -y --default-toolchain none --no-modify-path
# 2. the pinned toolchain
elan toolchain install leanprover/lean4:v4.34.0
# 3. the locked project (section 2); the lean-toolchain file selects the pin
cd autoresearch/lean-loop-260925/lean && lake build        # Defs + audit exe
# 4. record identity
lean --version; lake --version; leanchecker --help | head -3
lean --help | grep -Ei 'json|memory|timeout|threads'       # confirm flag names
du -sh ~/.elan
```

Estimated size and time. These are estimates, not measurements; section 1
step 4 measures them.

| Item | Download | On disk | Time |
|---|---|---|---|
| elan | 2.2 MB | ~10 MB | < 1 min |
| Lean v4.34.0 toolchain | 562 MB (.tar.zst) | 2.5-3.5 GB (unmeasured) | 3-10 min, bandwidth bound |
| Locked project build (core only) | 0 | < 20 MB | < 1 min |
| Optional Batteries v4.34.0 (only if section 3 needs list lemmas missing from core) | ~10 MB git | 0.2-0.5 GB .lake | 5-15 min |
| Optional finalize judge: comparator + lean4export v4.34.0 | ~5 MB git | 0.1-0.3 GB | 5-10 min |

51 GiB is free, so disk is not a constraint, although the volume is 88% used.
To uninstall, run `elan self uninstall` (or `brew uninstall elan-init`),
then `rm -rf ~/.elan autoresearch/lean-loop-260925/lean/.lake`.

The plan is to start with **core only**. Recent core ships the list API these
statements need: `List.foldl_append`, `eraseIdx`, `getLast?`, `dropLast`,
`replicate`, `Perm`, and the `omega`/`simp`/`grind` tactics. Add Batteries
only if the reference proofs (Phase 2, step 2) show a real gap. If you add
it, pin it as `rev = "v4.34.0"`.

## 2. Locked Lean project

```
autoresearch/lean-loop-260925/lean/          (locked; sha256 in lean.lock.json)
  lean-toolchain        leanprover/lean4:v4.34.0
  lakefile.toml
  LrxLean.lean          import LrxLean.Defs
  LrxLean/Defs.lean     model + statement Props + milestone Props (no theorems, no sorry)
  LrxLean/Conformance.lean   trusted rfl/decide examples generated from src/lrx/state.py
  Audit.lean            trusted audit executable (section 5, stage C)
autoresearch/lean-loop-260925/reference/     (NOT on any sandbox read path; see risk R10)
  Reference.lean        human/agent reference proofs proving statements are provable in core
autoresearch/lean-loop-260925/challenge/     (finalize only; comparator Challenge module)
  Challenge.lean        `theorem L1 : LRX.Stmt.L1 := sorry` etc.
```

`lakefile.toml`:

```toml
name = "lrxlean"
version = "0.1.0"
defaultTargets = ["LrxLean", "lrxaudit"]

[[lean_lib]]
name = "LrxLean"

[[lean_exe]]
name = "lrxaudit"
root = "Audit"
```

`LrxLean/Defs.lean`. This is the model. It mirrors `src/lrx/state.py`
`apply_L`, `apply_R`, `apply_X`, `canonical_root` and `remove_zero_at`.

```lean
/-! LRX visible-vector model (locked module; candidates cannot edit it).
Vectors are `List Nat`: labels 1..m once, zeros for the r blank atoms.
Letters act left to right, as in src/lrx/state.py and the m=8 checker. -/
namespace LRX

inductive Gen where
  | L | R | X
  deriving DecidableEq, Repr

/-- L: (x0,x1,...,x_{n-1}) ↦ (x1,...,x_{n-1},x0) -/
def rotL : List Nat → List Nat
  | [] => []
  | a :: t => t ++ [a]

/-- R: (x0,...,x_{n-1}) ↦ (x_{n-1},x0,...,x_{n-2}) -/
def rotR (v : List Nat) : List Nat :=
  match v.getLast? with
  | none => []
  | some a => a :: v.dropLast

/-- X: exchange the first two entries (identity on length < 2) -/
def swap12 : List Nat → List Nat
  | a :: b :: t => b :: a :: t
  | v => v

def step : Gen → List Nat → List Nat
  | .L, v => rotL v
  | .R, v => rotR v
  | .X, v => swap12 v

/-- `exec [g₁, g₂] v = step g₂ (step g₁ v)` -/
def exec (w : List Gen) (v : List Nat) : List Nat :=
  w.foldl (fun u g => step g u) v

/-- canonical root (1,...,m,0^r) -/
def root (m r : Nat) : List Nat :=
  (List.range m).map (· + 1) ++ List.replicate r 0

/-! Free reduction (cancel LR, RL, XX) -/
def inv : Gen → Gen
  | .L => .R
  | .R => .L
  | .X => .X

/-- stack holds the reduced prefix reversed; top = last kept letter -/
def push (st : List Gen) (g : Gen) : List Gen :=
  match st with
  | h :: t => if h = inv g then t else g :: h :: t
  | [] => [g]

def freeReduce (w : List Gen) : List Gen :=
  (w.foldl push []).reverse

def Reduced : List Gen → Prop
  | a :: b :: t => b ≠ inv a ∧ Reduced (b :: t)
  | _ => True

/-! Deletion of one marked atom at position j of a length-n vector
(group's Lemma 4 rule; research/problem.md marked-zero table) -/
def track (n j : Nat) : Gen → Nat
  | .L => if j = 0 then n - 1 else j - 1
  | .R => if j = n - 1 then 0 else j + 1
  | .X => if j < 2 then 1 - j else j

/-- L kept iff first atom not deleted; R iff last not deleted; X iff both kept -/
def keep (n j : Nat) : Gen → Bool
  | .L => j != 0
  | .R => j != n - 1
  | .X => decide (2 ≤ j)

/-- (projected word, final position of the marked atom) -/
def proj (n : Nat) : Nat → List Gen → List Gen × Nat
  | j, [] => ([], j)
  | j, g :: w =>
    let r := proj n (track n j g) w
    (if keep n j g then g :: r.1 else r.1, r.2)

/-! Stretch macros (group's Lemma 1 table) -/
def rep (w : List Gen) : Nat → List Gen
  | 0 => []
  | k + 1 => w ++ rep w k

/-- X on (0^{1+z}, a)  ↦  L^z X (RX)^z -/
def macroZL (z : Nat) : List Gen := rep [.L] z ++ [.X] ++ rep [.R, .X] z
/-- X on (a, 0^{1+z})  ↦  X (LX)^z R^z -/
def macroLZ (z : Nat) : List Gen := [.X] ++ rep [.L, .X] z ++ rep [.R] z

namespace Stmt
-- Targets (section 3) and milestones (section 3.4) are Props here, so the
-- candidate proves `theorem L1 : LRX.Stmt.L1`, and the audit compares
-- the proof's type with `Expr.const LRX.Stmt.L1 []`.
end Stmt
end LRX
```

`Conformance.lean` is trusted and generated once from Python. For every word
of length ≤ 6 on every permutation of `(1,2,3,0,0)`, and on a sample at
m=4, r=2, it emits `example : exec <w> <v> = <python result> := by decide`
(or `rfl`). It also adds non-vacuity examples for every statement's
hypotheses, for example
`example : exec (proj 3 0 [.L,.X]).1 ([0,1,2].eraseIdx 0) = ... := by decide`.
It is built as part of `lake build`. A definition bug that made a statement
vacuous would then fail the build (risk R1).

## 3. Target statements

These statements were checked on finite cases before any Lean exists. A
Python mirror of the definitions above
(`scratchpad/simcheck.py`, not committed) ran 69,219 checks with 0
failures. It confirmed that the mirror agrees with `src/lrx/state.py` on
words ≤ 6 over `(1,2,3,0,0)`. It confirmed L1 for n ≤ 4 and words ≤ 6.
It confirmed L2 for n = 2..5, all j, and words ≤ 6. It confirmed the
Lemma-4 sort corollary with BFS-shortest sorting words at
(m,r) ∈ {(3,1),(3,2),(2,3),(1,1),(4,1)}. It confirmed L3 and L3b for
z ≤ 6. For **n = 1**, L2 fails in 518 cases: X is the identity there, but
`track` sends position 0 to 1. The hypothesis `2 ≤ v.length` is therefore
necessary, not decorative.

Expected difficulty in core Lean: L1 is easy to medium. L3 is medium and
needs a generalised induction. L2 is medium to hard, because of case
analysis on `eraseIdx` against `getLast?`/`dropLast`. The task ordering
L1 < L2 < L3 may therefore not match actual proof difficulty. The score
weights all three equally and reports each one separately.

### 3.1 L1: free reduction preserves execution

```lean
def Stmt.L1 : Prop :=
  ∀ (w : List Gen) (v : List Nat), exec (freeReduce w) v = exec w v
```

Expected route: `exec_append` (foldl_append), then `step (inv g) (step g v) = v`
(rotR∘rotL, rotL∘rotR, swap12∘swap12), then the stack invariant
`exec (st.reverse ++ w) v = exec ((w.foldl push st).reverse) v` by
induction on w generalising st.

### 3.2 L2: Lemma 4, one marked atom (group's Lemma 4, single-atom case)

```lean
def Stmt.L2 : Prop :=
  ∀ (v : List Nat) (j : Nat) (w : List Gen), 2 ≤ v.length → j < v.length →
    exec (proj v.length j w).1 (v.eraseIdx j)
      = (exec w v).eraseIdx (proj v.length j w).2
```

The statement does not require `v[j] = 0`, because the commutation holds
for any marked entry. The zero only matters for the sort corollary M7. The
group deletes several atoms at once. That case follows by iterating L2 on
the shortened vector, which a later stretch target could state. Letters
are dropped by position (`keep`). This differs from the metric in
`research/problem.md` ("count a projection step exactly when u changes"),
which is at most the kept count. That metric is not formalised here.

### 3.3 L3: Lemma 1 stretch macro for X on (0^{1+z}, a), all z

```lean
def Stmt.L3 : Prop :=
  ∀ (z a : Nat) (w : List Nat),
    exec (macroZL z) (List.replicate (z + 1) 0 ++ a :: w)
      = a :: (List.replicate (z + 1) 0 ++ w)
```

This is the physical form of "after the macro, the vector is the stretch
of the atomic vector after X". It holds for every `a`, not only labels.
The proof needs the invariant
`exec (rep [.R,.X] k) (a :: replicate (1+i) 0 ++ w ++ replicate k 0) = a :: replicate (1+i+k) 0 ++ w`,
proved by induction on k generalising i. Finding that generalisation is
the actual difficulty. The prompt will not reveal it.

### 3.4 Milestones (fixed partial-credit statements, also in `LRX.Stmt`)

| Id | Statement (all ∀-closed) | Serves |
|---|---|---|
| M1 | `exec (p ++ s) v = exec s (exec p v)` | L1, L2, L3 |
| M2 | `step (inv g) (step g v) = v` | L1 |
| M3 | `Reduced (freeReduce w)` | L1 (companion: output is reduced) |
| M4 | `(exec w v).length = v.length` | L2, M7 |
| M5 | `2 ≤ v.length → j < v.length → (exec w v)[(proj v.length j w).2]? = v[j]?` | L2 (tracked atom is the marked one) |
| M6 | `(proj n j w).1.length ≤ w.length` | L2 (projection never lengthens) |
| M7 | `2 ≤ m + r → v[j]? = some 0 → exec w v = root m r → exec (proj (m + r) j w).1 (v.eraseIdx j) = root m (r - 1)` | Lemma 4 proper: projected word sorts projected input |
| M9 | `exec (macroLZ z) (a :: (List.replicate (z + 1) 0 ++ w)) = List.replicate (z + 1) 0 ++ a :: w` | L3 twin macro |

M8 (L3 generalised to an arbitrary block `bs` of length z+1) is omitted on
purpose. Listing it would give away the generalisation.

## 4. Candidate contract

- A candidate is **one text body**: the last fenced ```` ```lean ```` block
  in the response, following the rule already used by
  `lift_backends.preflight_source`. The cap is 32 KiB. Truncated output
  (`finish_reason` length) is rejected before evaluation.
- The evaluator writes `Cand.lean` as a trusted header, then the body, then
  a trusted footer:
  ```lean
  import LrxLean.Defs
  set_option maxHeartbeats 400000
  set_option maxRecDepth 2048
  open LRX
  namespace Cand
  <candidate body>
  end Cand
  ```
- Required names: `Cand.L1 : LRX.Stmt.L1`, `Cand.L2`, `Cand.L3`, and
  optionally `Cand.M1 … Cand.M9` with the matching Stmt types. Proofs start
  with `unfold Stmt.L1` or `intro …`. The seed file shows this pattern with
  `sorry` bodies. Any other `theorem`, `lemma` or `def` is allowed as an
  auxiliary declaration.
- The candidate **cannot** change statements. They live in the imported
  `LrxLean/Defs.olean`. That file is built by a trusted step before any
  candidate exists, sits on a read-only sandbox path, and its sha256 and the
  sha256 of `Defs.lean` are checked against `lean.lock.json` before every
  evaluation. Redeclaring `LRX.*` names is a Lean error.
- Credit is given for sorry-free proofs whose axioms are only
  `{propext, Classical.choice, Quot.sound}`. `sorry` is syntactically
  allowed so that incomplete files still produce feedback, but any
  declaration that depends on `sorryAx` earns nothing. `native_decide`
  (axioms `Lean.ofReduceBool` and `Lean.trustCompiler`) is forbidden. It
  cannot help with these ∀-statements anyway.
- Lexical ban (preflight, before any process starts; this is defence in
  depth, and the semantic checks in section 5 are the real guarantee):
  `import`, `axiom`, `unsafe`, `implemented_by`, `extern`, `@[init`,
  `initialize`, `builtin_`, `set_option`, `macro`, `macro_rules`, `syntax`,
  `elab`, `elab_rules`, `notation`, `infix`, `infixl`, `infixr`, `prefix`,
  `postfix`, `run_cmd`, `run_elab`, `run_meta`, any `#` command (`#eval`,
  `#exit`, `#print`, `#check`, ...), `native_decide`, `+native`,
  `ofReduceBool`, `trustCompiler`, `debug.`, `opaque`, `partial`,
  `namespace`, `section`, `end`, `open Lean`, identifiers beginning with
  `Lean.`, `IO.`, `System.` or `Std.`, and `csimp`. Any hit makes the
  candidate INVALID with the rule named. The ban is on raw text, comments
  included, because an overmatch is only a lost proposal.

## 5. Evaluator (`integrations/lean_evaluator.py`, new, search side; recommend a human add it to TRUSTED)

Each stage is a separate process. Each is wrapped in a Seatbelt profile
built from `program_sandbox.sandbox_profile`, following the pattern in
`program_evaluator._run_case` (Popen with `start_new_session`, rlimits in
`preexec_fn`, `killpg` in `finally`). Each gets a minimal env:
`PATH=<toolchain>/bin:/usr/bin:/bin`, `HOME`/`TMPDIR` set to the stage
scratch, `LEAN_PATH=<toolchain>/lib/lean:<locked>/.lake/build/lib/lean`,
no ELAN variables and no credentials. The toolchain binaries are called
**directly** (`~/.elan/toolchains/leanprover--lean4---v4.34.0/bin/lean`),
not through the elan proxy. The evaluator refuses to run if
`lean --version` differs from the pin.

Sandbox profile for Lean. It adds to the existing profile and needs a new
parameter or a local variant, so `program_sandbox.py` itself is unchanged.
Reads are allowed on the toolchain directory, the locked build directory
(read-only), `/usr/lib`, `/System` and `/private/etc`. Writes are allowed
only on the stage scratch directory. There is **no** network or loopback
port. Candidate stages do **not** get the `(allow process*)` grant. They
get `process-exec` for the single binary only, and `process-fork` is
denied. Phase 2 measures whether Lean needs `mach-lookup`, and drops the
grant if it does not. Rlimits: CPU = wall + 1 s; FSIZE 64 MB; NOFILE 4096,
because Lean maps many `.olean` files; tune this at install. macOS ignores
RLIMIT_AS, so memory is capped with `lean -M/--memory` (flag name to be
confirmed by `lean --help`) plus a parent watchdog that kills the process
group above 4 GB RSS. Threads are set to 1 for determinism.

Stages:

1. **Preflight**: fence extraction, size cap, lexical ban, and the
   `lean.lock.json` hash check.
2. **Stage A, elaborate** (sandboxed, wall 60 s):
   `lean --json -o Cand.olean Cand.lean` in scratch A. The run collects
   every message (severity, position, text; unsolved-goal errors carry
   the goal state). `maxHeartbeats` is the deterministic limit and wall
   time is only a backstop. Exceeding wall time gives **INCOMPLETE**, never
   a mathematical verdict (AGENTS.md).
3. **Stage B, kernel replay** (sandboxed, wall 60 s):
   `leanchecker Cand`, with Cand.olean read-only from scratch A. This
   catches declarations added without kernel checking, for example through a
   ban-evading `debug.skipKernelTC` or `modifyEnv`. Finalize also runs
   `leanchecker --fresh Cand`.
4. **Stage C, audit** (sandboxed, wall 30 s, fresh scratch C that stage A
   could never write). This runs the trusted `lrxaudit` executable, built
   from locked `Audit.lean` before any candidate existed. It is called with
   `lrxaudit <nonce> Cand`, and the nonce is generated after stage A has
   been killed. Using core `Lean.importModules` **without enabling
   initializers**, it does the following for each required name:
   - The name exists and is a `thmInfo`.
   - Its type is exactly `Expr.const LRX.Stmt.<id> []`.
   - Its `CollectAxioms` set is a subset of
     `{propext, Classical.choice, Quot.sound}`.
   - The `LRX.Stmt.<id>` value is identical to the one in a second
     environment that imports only `LrxLean.Defs`.

   For auxiliary declarations it lists the module's own theorems that are
   sorry-free and axiom-clean. It computes which ones are reachable, via
   `getUsedConstants`, from any target or milestone declaration, including
   ones that still have `sorry`. It deduplicates them by the hash of their
   type. It prints one JSON line containing the nonce to stdout. The parent
   reads only stdout, never a file, and rejects output whose nonce is wrong.
5. **Score** (parent, exact rationals, then `float(Fraction)`, per the
   TRACE-AUDIT defect 1 lesson):
   ```
   T  = (#targets closed among L1,L2,L3) / 3
   M  = (#milestones closed) / 8
   A  = min(10, #qualifying auxiliary lemmas) / 10    # reachable, sorry-free, deduped
   P  = min(0.05, 0.01 * #error messages in stage A)
   combined_score = T + 0.2*M + 0.05*A - P            # range [-0.05, 1.25]
   INVALID (preflight/ban/hash) or stage B failure  -> combined_score = -1, status INVALID
   INCOMPLETE (wall/memory)                         -> combined_score = -1, status INCOMPLETE
   ```
   One extra closed target (+1/3) always outweighs all milestone and
   auxiliary credit plus the maximum penalty (0.25 + 0.05). The task's
   request to reward "count of declared lemmas that typecheck" is used only
   in this filtered form. A raw count is gamed at once by
   `theorem t1 : 1 = 1 := rfl` repeated (risk R6). Per-target and
   per-milestone booleans are returned as extra metrics. `combined_score`
   is always present, so SkyDiscover never averages the other numbers.
6. **Cache**: the key is sha256 of the toolchain id, the Defs hash, the
   `Audit` binary hash, the evaluator version and the body.

Cost per candidate is expected to be 5-20 s, because the project is core
only and has no Mathlib import. This is unmeasured.

**Finalize (independent second judge).** For each claimed target, run
`leanchecker --fresh`. Then run `leanprover/comparator` v4.34.0 with
Challenge = `challenge/Challenge.lean` (imports Defs,
`theorem L1 : LRX.Stmt.L1 := sorry`) and Solution = `Cand` re-emitted
with the same theorem names at top level, and
`permitted_axioms = [propext, Quot.sound, Classical.choice]`. On macOS this
needs a **Seatbelt landrun shim**, a new trusted script. The shim
translates comparator's
`--ro/--rw/--rwx/--rox/--env/-- cmd` arguments into a
`sandbox_profile`. It replaces comparator's `--ro /` with the narrow
read allowlist above, so the sandboxed build cannot read `~` (risk R8).
The last step is a human read of the proof text before anything enters
`research/claims.md`.

## 6. Integration with broker and engines

- `integrations/lean_backends.py` (new, search side) mirrors
  `lift_backends`:
  - `LeanVerifier` has the same `evaluate(source, parent_id, *, final)`
    and `serve()` methods: a loopback `ThreadingHTTPServer` on `/evaluate`
    with request size caps.
  - The engine worker is launched through the same `_launch` pattern.
    It runs under Seatbelt with loopback grants only for the broker and
    verifier ports, and `killpg` on wall-time expiry.
  - `approval_material`/`check_approval` hashes, per-arm ledgers,
    first-prompt capture and guard, and `_finish` with independent
    re-audit are reused by import. `lift_backends.py` itself is not
    edited, because it is approval-hashed.
  - The verifier runs in the parent, as for lift, so Lean sandboxes are
    not nested inside the worker sandbox.
- Feedback packet (development signal, ≤ 3,000 chars, fenced as data):
  - A status line per target and milestone (closed / sorry / error /
    missing) and the current best from **any** scope. This avoids
    TRACE-AUDIT defect 7.
  - The first ≤ 3 stage-A errors, each with `line:col` and trimmed to 400
    chars, with unsolved-goal states kept.
  - The locked statement text of the first unclosed target, and the list of
    axioms that disqualified a declaration.
  - It never contains `Audit.lean`, the evaluator source, reference proofs,
    scratch paths or environment.
- GEPA (native 0.1.4): there is one text component (`lean_body`). The
  dataset has 11 instances (L1-L3 and M1-M7, M9), each `{"id": ...}`.
  Instance score is 1 if the named declaration is closed and 0 otherwise.
  Instance feedback is the errors inside that declaration's line range plus
  its statement.
  - Because the file is cached by hash, one Lean run serves every instance
    of a candidate.
  - Set `reflection_minibatch_size = 3` for this multi-task set, and
    100-300 metric calls.
  - 11 instances is at the low edge for instance-level Pareto selection.
    Expect weak Pareto signal.
  - The training set must not include the validation set's instances. This
    avoids TRACE-AUDIT defect 11. With 11 instances, use train = all and
    no separate validation.
- SkyDiscover AdaEvolve:
  - The evaluator shim returns `EvaluationResult(metrics={combined_score,
    per-id booleans}, artifacts={'feedback': packet})`.
  - Set `cascade_evaluation: False`, **`random_seed` fixed**
    (GUARD-NOTE), `inject_evaluator_context` **off**,
    `num_context_programs` 1 (TRACE-AUDIT defect 10), and full rewrites
    (`diff_based_generation: False`) because files are small. Check
    whether `language: "lean"` is accepted. If it is not, keep "python" and
    use a Lean-specific template.
- EvoX: **excluded from Track 3.** Its outer loop writes and runs
  LLM-generated Python search strategies, which conflicts with AGENTS.md.
  If it is ever enabled, keep `evox_strategy_evolution_enabled` False.
- Controls, needed before any engine claim:
  - (a) The seed: stubs with `sorry`, score 0.
  - (b) A deterministic, LLM-free **tactic sweep**. For each target and
    milestone it tries a fixed list, such as `simp [exec, step, ...]`,
    `induction w generalizing v <;> simp_all [...]`, `grind`, `omega`,
    `decide` and `exact?`. It is cheap and sets the floor.
  - (c) The sequential single-model control, as in earlier campaigns.
- Pre-registered rules:
  - Success means an engine arm closes a target that control (b) did not.
    The result must be confirmed by finalize (leanchecker --fresh,
    comparator and a human read).
  - Kill: no gain in milestones plus targets over control (b) after 60
    proposals in an arm.
  - Live calls need the usual explicit approval hash.

## 7. Lean-specific leakage and reward-hacking risks

| # | Exploit | Mitigation |
|---|---|---|
| R1 | Vacuous or wrong statement, e.g. a definition bug that makes L2 trivial | Python cross-check (done, finite). `Conformance.lean` decide-examples against `src/lrx/state.py`. Non-vacuity examples. Reference proofs. Human review before lock |
| R2 | `axiom`, `sorry`, `admit`, `sorryAx` | Per-declaration axiom allowlist in stage C, plus the lexical ban |
| R3 | `native_decide` / `ofReduceBool` / `trustCompiler` | Axiom allowlist, plus the lexical ban |
| R4 | Skipping the kernel: `set_option debug.skipKernelTC`, `modifyEnv`/`addDeclWithoutChecking` via metaprograms | `set_option` and all meta commands banned. Stage B `leanchecker` replays every declaration through the kernel. Finalize uses `--fresh` and comparator |
| R5 | Changing what the statement means: custom `notation`, `macro_rules` or elaborators that reinterpret the target at the check site, `open ... in` tricks, redefining `exec` in another namespace | Statements are Props in the locked olean. Stage C compares `Expr` types structurally, **not text**, in a process that does not run candidate initializers. All syntax extensions are banned |
| R6 | Farming partial credit with many trivial lemmas | Auxiliary credit is capped at 0.05. It counts only lemmas reachable from a target or milestone declaration, deduplicated by type hash. Milestones are a fixed list |
| R7 | Changing imports or the statement module (`import Mathlib`, a local `LrxLean` shadow, a `.lake` write) | Candidate body cannot contain `import`; the header is trusted. The locked build directory is read-only in Seatbelt. Hashes are checked every evaluation. LEAN_PATH is fixed by the parent |
| R8 | Reading secrets or host files at compile time and echoing them through error messages into the LLM prompt (exfiltration) | `#eval`/`IO`/`run_cmd` banned. The Seatbelt read allowlist contains no `~`, no repo and no reference directory. The env is scrubbed. There is no network. The packet is capped |
| R9 | A process that outlives the stage and forges the verdict | Stage A cannot fork or exec. `killpg` runs in `finally`. Stage C uses a fresh scratch directory. The verdict comes via stdout with a post-stage-A nonce |
| R10 | Reference proofs leaking into feedback or readable paths | Kept outside the lake project and every sandbox read path. Never in prompts |
| R11 | Resource abuse: `decide` blowups, deep recursion, output floods | `maxHeartbeats`/`maxRecDepth` fixed in the header. CPU and FSIZE rlimits. Memory flag plus watchdog. Message bytes capped. Timeout gives INCOMPLETE |
| R12 | Toolchain drift making old verdicts incomparable | Pin v4.34.0. The evaluator checks `lean --version`. The toolchain id is part of the cache key and the manifest |
| R13 | Self-injection: candidate strings echoed in errors steer the next proposal | Packet text is fenced and labelled as data and truncated. Low severity |
| R14 | Kernel or `Nat`-GMP bug | Out of scope. The optional nanoda second kernel needs Rust (a new dependency) and is not planned |

## 8. Phase 2 checklist (after install approval)

1. Install per section 1. Record `lean --version`, `du -sh ~/.elan` and the
   `lean --help` flag names in `INSTALL-LOG.md`.
2. `lake build` the locked project, including `Conformance.lean`. Write
   `reference/Reference.lean` with proofs of L1, L2, L3 and M1-M9 in
   core. If core lacks a needed lemma, record which one and decide on
   Batteries. Lock the hashes in `lean.lock.json`.
3. Build `lrxaudit`. Check it against hand-made adversarial files:
   `axiom`, `sorry`, `native_decide`, the `skipKernelTC` form (with the ban
   disabled in the test harness), a wrong type under the right name, a
   redefined `exec`, and trivial-lemma spam. Every one must be rejected or
   earn zero credit.
4. `tests/test_search_lean_*.py`. Mock tests need no Lean: preflight,
   bans, packet and scoring. Integration tests are skipped when the pinned
   toolchain is absent. Then run the three AGENTS.md verify commands and
   `python tools/orchestrator.py trusted`.
5. Run the tactic-sweep control and the mock-HTTP engine smokes. Capture
   the first prompts. Live arms only after an explicit approval hash.

## 9. Open questions for the human

- Should `integrations/lean_evaluator.py`, `Audit.lean` and the landrun
  shim be added to TRUSTED (recommended), with a re-lock after review?
- Does equal weight on L1, L2 and L3 match the research value? L2/M7 is
  the one that formalises the group's Lemma 4.
- Should a later stretch target state the full Lemma 1? That would be
  execution of the lifted word on a stretched atom vector, for all
  stretch vectors z, and would need a block-structured vector type.
