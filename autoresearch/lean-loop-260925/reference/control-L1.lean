-- Human-written reference proof of L1 (pipeline control), in candidate body format:
-- the evaluator wraps it in its trusted header (LrxLean.Defs, open LRX, scope Cand) and footer.
theorem exec_append (p s : List Gen) (v : List Nat) : exec (p ++ s) v = exec s (exec p v) := by
  simp only [exec, List.foldl_append]

theorem exec_cons (g : Gen) (w : List Gen) (v : List Nat) : exec (g :: w) v = exec w (step g v) := rfl

theorem exec_nil (v : List Nat) : exec [] v = v := rfl

theorem rotR_rotL (v : List Nat) : rotR (rotL v) = v := by
  cases v with
  | nil => rfl
  | cons a t => simp [rotL, rotR]

theorem rotL_rotR (v : List Nat) : rotL (rotR v) = v := by
  rcases List.eq_nil_or_concat v with h | ⟨L, b, h⟩
  · subst h; rfl
  · subst h; simp [rotL, rotR]

theorem swap12_swap12 (v : List Nat) : swap12 (swap12 v) = v := by
  match v with
  | [] => rfl
  | [_] => rfl
  | _ :: _ :: _ => rfl

theorem step_inv (g : Gen) (v : List Nat) : step (inv g) (step g v) = v := by
  cases g
  · exact rotR_rotL v
  · exact rotL_rotR v
  · exact swap12_swap12 v

theorem inv_inv (g : Gen) : inv (inv g) = g := by cases g <;> rfl

theorem exec_push (st : List Gen) (g : Gen) (v : List Nat) :
    exec (push st g).reverse v = exec (st.reverse ++ [g]) v := by
  cases st with
  | nil => rfl
  | cons h t =>
    simp only [push]
    split
    · rename_i hh
      subst hh
      simp only [List.reverse_cons, exec_append, exec_cons, exec_nil]
      have key := step_inv (inv g) (exec t.reverse v)
      rw [inv_inv] at key
      exact key.symm
    · simp [List.reverse_cons, List.append_assoc]

theorem exec_fold (w st : List Gen) (v : List Nat) :
    exec (w.foldl push st).reverse v = exec (st.reverse ++ w) v := by
  induction w generalizing st with
  | nil => simp
  | cons g w ih =>
    rw [List.foldl_cons, ih, exec_append, exec_push, ← exec_append, List.append_assoc]
    rfl

theorem L1 : Stmt.L1 := by
  intro w v
  have h := exec_fold w [] v
  simpa [freeReduce] using h
