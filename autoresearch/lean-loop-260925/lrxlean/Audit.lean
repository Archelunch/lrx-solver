import Lean
/-! Trusted audit executable (stage C). Reads a kernel-replayed candidate module
without running its initializers (`loadExts := false`), and prints one JSON
line that echoes the caller's nonce. It never trusts any environment extension
of the candidate olean: axioms are recollected from the constants themselves. -/
open Lean

def ids : List String := ["L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M9"]
def allowed : List Name := [``propext, ``Classical.choice, ``Quot.sound]

/-- Constants reachable from `n` (types, values, constructors) and the axioms among them.
Unknown constants are reported as axioms `unknown.<name>` so the audit fails closed. -/
partial def visit (env : Environment) (n : Name) : StateM (NameSet × NameSet) Unit := do
  if (← get).1.contains n then return
  modify fun (s, a) => (s.insert n, a)
  match env.find? n with
  | none => modify fun (s, a) => (s, a.insert (`unknown ++ n))
  | some ci =>
    if ci matches .axiomInfo _ then modify fun (s, a) => (s, a.insert n)
    let mut cs := ci.type.getUsedConstants
    if let some v := ci.value? (allowOpaque := true) then cs := cs ++ v.getUsedConstants
    if let .inductInfo v := ci then cs := cs ++ v.ctors.toArray
    for c in cs do visit env c

def axiomsOf (env : Environment) (n : Name) : Array Name :=
  ((visit env n).run ({}, {})).2.2.toArray.qsort Name.lt

def moduleOf (env : Environment) (n : Name) : Option Name :=
  (env.getModuleIdxFor? n).bind fun i => env.header.moduleNames[i.toNat]?

/-- Candidate-module constants reachable from `n` through types and values. -/
partial def localReach (env : Environment) (mod : Name) (n : Name) : StateM NameSet Unit := do
  if (← get).contains n then return
  if moduleOf env n != some mod then return
  modify (·.insert n)
  match env.find? n with
  | none => return
  | some ci =>
    let mut cs := ci.type.getUsedConstants
    if let some v := ci.value? (allowOpaque := true) then cs := cs ++ v.getUsedConstants
    for c in cs do localReach env mod c

def main (args : List String) : IO UInt32 := do
  let [nonce, modStr] := args | IO.eprintln "usage: lrxaudit NONCE MODULE"; return 2
  let mod := modStr.toName
  searchPathRef.set (← addSearchPathFromEnv {})
  let env ← importModules #[{ module := mod }] {} (trustLevel := 0) (loadExts := false)
  let clean (axs : Array Name) := axs.all (allowed.contains ·)
  let mut targets : Array (String × Json) := #[]
  let mut roots : Array Name := #[]
  for id in ids do
    let cname := `Cand ++ id.toName
    let sname := `LRX.Stmt ++ id.toName
    let stmtOk := moduleOf env sname == some `LrxLean.Defs
    let status ← match env.find? cname with
      | none => pure ("missing", #[])
      | some ci =>
        if moduleOf env cname != some mod then pure ("foreign", #[]) else
        let axs := axiomsOf env cname
        if !(ci matches .thmInfo _) then pure ("not_theorem", axs)
        else if !stmtOk || ci.type != mkConst sname then pure ("wrong_type", axs)
        else if axs.contains ``sorryAx then pure ("sorry", axs)
        else if !clean axs then pure ("bad_axioms", axs)
        else pure ("closed", axs)
    -- Only closed roots credit helpers: a `sorry` or wrong-type stub that merely
    -- mentions lemmas (e.g. `have := t1`) must not earn helper credit.
    if status.1 == "closed" then roots := roots.push cname
    targets := targets.push (id, Json.mkObj [("status", toJson status.1),
      ("axioms", toJson (status.2.map toString))])
  let reach := ((roots.forM (localReach env mod)).run {}).2
  -- Root statement types are pre-seeded so a restated target is not a helper.
  let mut seenTypes : Std.HashSet UInt64 := {}
  for r in roots do
    if let some ci := env.find? r then seenTypes := seenTypes.insert ci.type.hash
  let mut aux : Array String := #[]
  for n in reach.toArray.qsort Name.lt do
    if roots.contains n || n.isInternal then continue
    let some ci := env.find? n | continue
    unless ci matches .thmInfo _ do continue
    unless clean (axiomsOf env n) do continue
    -- A helper must talk about the LRX model: its type uses a LrxLean.Defs constant.
    unless ci.type.getUsedConstants.any (moduleOf env · == some `LrxLean.Defs) do continue
    if seenTypes.contains ci.type.hash then continue
    seenTypes := seenTypes.insert ci.type.hash
    aux := aux.push n.toString
  IO.println (Json.mkObj [("nonce", toJson nonce), ("module", toJson modStr),
    ("targets", Json.mkObj (targets.toList)), ("aux", toJson aux)]).compress
  return 0
