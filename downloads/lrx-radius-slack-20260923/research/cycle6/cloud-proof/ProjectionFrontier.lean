import Mathlib.Tactic.Linarith

/-! Conditional integer consequences of a proposed finite certificate.
No LRX distance or DP value is asserted by this file. -/
namespace LRX.ProjectionFrontier

theorem obstruction {q s : Int}
    (hshort : q+s ≤ 48) (hexclusion : q ≤ 42 → 49 ≤ q+s) :
    43 ≤ q ∧ s ≤ 5 := by
  have hq43 : 43 ≤ q := by
    by_contra h
    have := hexclusion (by omega)
    omega
  constructor <;> omega

theorem geodesic_losses {q s : Int} (hlen : q+s = 47)
    (hexclusion : q ≤ 42 → 49 ≤ q+s) : 43 ≤ q ∧ s ≤ 4 := by
  have hq43 : 43 ≤ q := by
    by_contra h
    have := hexclusion (by omega)
    omega
  constructor <;> omega

theorem constrained_losses {q s : Int} (hlen : q+s = 49)
    (hq : q ≤ 42) : 7 ≤ s := by omega

theorem allowance_nontrivial {P m delta : Int}
    (hd : delta ≤ m-3) : P+delta < P+m-2 := by omega

theorem frontier_repair {H P delta : Int}
    (hdelta : H-P ≤ delta) : H ≤ P+delta := by omega

#print axioms obstruction
#print axioms geodesic_losses
#print axioms constrained_losses
#print axioms allowance_nontrivial
#print axioms frontier_repair
end LRX.ProjectionFrontier
