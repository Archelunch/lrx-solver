theorem M1 : Stmt.M1 := by
  unfold Stmt.M1 exec
  intro p s v
  exact List.foldl_append

theorem step_length (g : Gen) (v : List Nat) : (step g v).length = v.length := by
  cases g with
  | L =>
    cases v with
    | nil => rfl
    | cons a t =>
      simp [step, rotL]
  | R =>
    simp [step, rotR]
    cases h : v.getLast? with
    | none =>
      have : v = [] := List.getLast?_eq_none_iff.mp h
      subst this
      rfl
    | some a =>
      have : v ≠ [] := by
        intro heq
        subst heq
        contradiction
      simp [List.length_dropLast, Nat.sub_add_cancel (List.length_pos_iff.mpr this)]
  | X =>
    cases v with
    | nil => rfl
    | cons a t =>
      cases t with
      | nil => rfl
      | cons b t' => rfl

theorem M4 : Stmt.M4 := by
  unfold Stmt.M4 exec
  intro w v
  induction w generalizing v with
  | nil => rfl
  | cons g w ih =>
    simp only [List.foldl_cons]
    rw [ih]
    exact step_length g v

theorem M6 : Stmt.M6 := by
  unfold Stmt.M6
  intro n j w
  induction w generalizing j with
  | nil => simp [proj]
  | cons g w ih =>
    simp only [proj]
    split
    · simp only [List.length_cons]
      exact Nat.succ_le_succ (ih (track n j g))
    · exact Nat.le_succ_of_le (ih (track n j g))

theorem rotL_rotR (v : List Nat) : rotL (rotR v) = v := by
  dsimp [rotR]
  cases h : v.getLast? with
  | none =>
    have : v = [] := List.getLast?_eq_none_iff.mp h
    subst this
    rfl
  | some a =>
    have hne : v ≠ [] := by
      intro heq
      subst heq
      contradiction
    have h_eq : v = v.dropLast ++ [a] := (List.dropLast_append_getLast? hne).symm.trans (by rw [h])
    conv => rhs; rw [h_eq]
    dsimp [rotL]

theorem rotR_rotL (v : List Nat) : rotR (rotL v) = v := by
  cases v with
  | nil => rfl
  | cons a t =>
    dsimp [rotL, rotR]
    rw [List.getLast?_append]
    · rw [List.dropLast_append]

theorem M2 : Stmt.M2 := by
  unfold Stmt.M2
  intro g v
  cases g with
  | X =>
    cases v with
    | nil => rfl
    | cons a t =>
      cases t with
      | nil => rfl
      | cons b t' => rfl
  | L =>
    dsimp [inv, step]
    exact rotR_rotL v
  | R =>
    dsimp [inv, step]
    exact rotL_rotR v

theorem L1 : Stmt.L1 := by
  unfold Stmt.L1
  sorry

theorem L2 : Stmt.L2 := by
  unfold Stmt.L2
  sorry

theorem L3 : Stmt.L3 := by
  unfold Stmt.L3
  sorry

theorem M3 : Stmt.M3 := by
  unfold Stmt.M3
  sorry

theorem M5 : Stmt.M5 := by
  unfold Stmt.M5
  sorry

theorem M7 : Stmt.M7 := by
  unfold Stmt.M7
  sorry

theorem M9 : Stmt.M9 := by
  unfold Stmt.M9
  sorry
