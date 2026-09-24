import Mathlib

/-! Scalar and telescoping parts of the zero-flux obstruction.
The correspondence between LRX words, cyclic zero gaps, and integer fluxes
is proved in the accompanying text and literal audits, not axiomatized here. -/

namespace CayleyPy.MultisetZeroFlux

theorem flux_path_identity (k : ℕ) (f c : ℕ → ℤ) :
    (∀ i < k, f (i+1) = f i + c i) →
    f k - f 0 = ∑ i ∈ Finset.range k, c i := by
  induction k with
  | zero => intro h; simp
  | succ k ih =>
    intro h
    have hk := h k (Nat.lt_succ_self k)
    have hs := ih (fun i hi => h i (Nat.lt_trans hi (Nat.lt_succ_self k)))
    rw [Finset.sum_range_succ]
    omega

theorem range_forces_half (m a b s : ℤ)
    (hspan : m-1 ≤ b-a) (ha : -s ≤ a) (hb : b ≤ s) :
    m/2 ≤ s := by omega

theorem slope_strictly_exceeds_target (m a b s beta : ℤ)
    (hspan : m-1 ≤ b-a) (ha : -s ≤ a) (hb : b ≤ s)
    (hslope : 2*s ≤ beta) : m-2 < beta := by omega

theorem no_uniform_single_word (m a b sa sb ba bb : ℤ)
    (hspan : m-1 ≤ b-a) (ha : -sa ≤ a) (hb : b ≤ sb)
    (hba : 2*sa ≤ ba) (hbb : 2*sb ≤ bb)
    (haTarget : ba ≤ m-2) (hbTarget : bb ≤ m-2) : False := by omega

theorem comparison_preserves_slope_lower_bound (beta oldSwaps newSwaps : ℤ)
    (hbeta : 2*oldSwaps ≤ beta) (hswaps : newSwaps ≤ oldSwaps) :
    2*newSwaps ≤ beta-oldSwaps+newSwaps := by omega

#print axioms flux_path_identity
#print axioms range_forces_half
#print axioms slope_strictly_exceeds_target
#print axioms no_uniform_single_word
#print axioms comparison_preserves_slope_lower_bound

end CayleyPy.MultisetZeroFlux
