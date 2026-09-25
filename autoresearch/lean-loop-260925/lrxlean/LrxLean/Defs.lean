/-! LRX visible-vector model (locked module; candidates cannot edit it).
Vectors are `List Nat`: labels 1..m once, zeros for the r blank atoms.
Letters act left to right, as in src/lrx/state.py (apply_L, apply_R, apply_X).
Lemma 1 (stretch macros) and Lemma 4 (deletion of one zero atom) are the
research group's results (autoresearch/verify-m8-260924/package, sections 3
and 6); the statements below formalise them and claim nothing about the open
conjecture. -/
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
/-! Targets. A candidate proves `theorem L1 : LRX.Stmt.L1` inside `namespace Cand`. -/

/-- L1: free reduction preserves execution. -/
def L1 : Prop :=
  ∀ (w : List Gen) (v : List Nat), exec (freeReduce w) v = exec w v

/-- L2: deleting one marked atom commutes with execution (group's Lemma 4, one atom). -/
def L2 : Prop :=
  ∀ (v : List Nat) (j : Nat) (w : List Gen), 2 ≤ v.length → j < v.length →
    exec (proj v.length j w).1 (v.eraseIdx j) = (exec w v).eraseIdx (proj v.length j w).2

/-- L3: group's Lemma 1 stretch macro for X on (0^{1+z}, a), all z. -/
def L3 : Prop :=
  ∀ (z a : Nat) (w : List Nat),
    exec (macroZL z) (List.replicate (z + 1) 0 ++ a :: w) = a :: (List.replicate (z + 1) 0 ++ w)

/-! Milestones (fixed partial-credit statements). -/
def M1 : Prop := ∀ (p s : List Gen) (v : List Nat), exec (p ++ s) v = exec s (exec p v)
def M2 : Prop := ∀ (g : Gen) (v : List Nat), step (inv g) (step g v) = v
def M3 : Prop := ∀ (w : List Gen), Reduced (freeReduce w)
def M4 : Prop := ∀ (w : List Gen) (v : List Nat), (exec w v).length = v.length
def M5 : Prop :=
  ∀ (v : List Nat) (j : Nat) (w : List Gen), 2 ≤ v.length → j < v.length →
    (exec w v)[(proj v.length j w).2]? = v[j]?
def M6 : Prop := ∀ (n j : Nat) (w : List Gen), (proj n j w).1.length ≤ w.length
def M7 : Prop :=
  ∀ (m r j : Nat) (v : List Nat) (w : List Gen), 2 ≤ m + r → v[j]? = some 0 →
    exec w v = root m r → exec (proj (m + r) j w).1 (v.eraseIdx j) = root m (r - 1)
def M9 : Prop :=
  ∀ (z a : Nat) (w : List Nat),
    exec (macroLZ z) (a :: (List.replicate (z + 1) 0 ++ w)) = List.replicate (z + 1) 0 ++ a :: w
end Stmt
end LRX
