import Mathlib.Tactic.Linarith

/-! Abstract silent-block accounting. The LRX transition correspondence and
normalization are proved in the cycle6 text, not assumed to be formalized here. -/
namespace LRX.MarkedZero

inductive Gate where
  | one | zero | last
  deriving DecidableEq

def silentDistance : Gate → Gate → Nat
  | .one, .last | .last, .one => 2
  | .one, .zero | .zero, .one | .zero, .last | .last, .zero => 1
  | _, _ => 0

theorem silent_distance_le_two (a b : Gate) : silentDistance a b ≤ 2 := by
  cases a <;> cases b <;> decide

theorem block_sum_bound (blocks : List Nat)
    (h : ∀ b ∈ blocks, b ≤ 2) : blocks.sum ≤ 2 * blocks.length := by
  induction blocks with
  | nil => simp
  | cons b bs ih =>
    have hb : b ≤ 2 := h b (by simp)
    have ht : ∀ x ∈ bs, x ≤ 2 := by
      intro x hx
      exact h x (by simp [hx])
    have hi := ih ht
    simp only [List.sum_cons, List.length_cons]
    omega

theorem normalized_cost_bound (q : Nat) (blocks : List Nat)
    (h : ∀ b ∈ blocks, b ≤ 2) (hn : blocks.length = q + 1) :
    q + blocks.sum ≤ 3*q + 2 := by
  have hs := block_sum_bound blocks h
  omega

/-- Arithmetic only: existence of the family word and its optimality are external. -/
theorem family_paid {k m P : Int} (hk : 2 ≤ k)
    (hm : 8*k-1 ≤ m) (hP : m ≤ P) :
    5*k-3 ≤ P ∧ 6*k-2 ≤ P+m-2 := by
  constructor <;> omega

theorem joint_budget {q s P m : Int} (hproj : q ≤ P)
    (hlost : s ≤ P-q+m-2) : q ≤ P ∧ q+s ≤ P+m-2 := by
  constructor
  · exact hproj
  · omega

#print axioms silent_distance_le_two
#print axioms block_sum_bound
#print axioms normalized_cost_bound
#print axioms family_paid
#print axioms joint_budget
end LRX.MarkedZero
