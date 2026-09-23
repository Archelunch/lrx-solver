Insights for potential campaigns (edited by the orchestrator). Train-side evidence only.
- phi is sound on a graph when phi >= 0, every non-root state has a neighbour (L, R or X) with phi
  at most phi - 1, and phi >= d; then d(v) <= phi(v). A sound phi with a descent argument valid for
  all m, r proves d <= phi; with max phi <= T it would prove the bound.
- Best (session 03 round 4): candidates/probes/6ff08052bb698f26.json, phi = a*e + k + c*u with
  c = floor(n/4), a = c + 2, u = tokens whose counterclockwise neighbour is a zero or a larger token
  (token 1 always counts). value_max 158/186/196 on m8r2/m8r3/m9r2 (T 42/48/52), 3.875x T. It
  generalises grok's 5d536a0608217df6 (4e + k + 2u, argument only for n <= 11). Why it descends: after
  an improving X the swapped pair dies and new improving cells can only appear at distance <= 1, so
  k' >= 2 forces du <= -1 and k' <= 1 allows du <= +1; this needs a >= c + 2 and
  a + c >= floor(n/2) + 1. Remaining slack: a is still about n/4 per unit of e. Next: a third level
  (charge the jump when u drops to a count of blocks or runs), or a smaller e.
- Previous (round 3): candidates/probes/ba656bf2c7e03787.json, phi = (floor(n/2)+1) * e + k,
  212/254/266, about 5x T (the first sound one, a5bd55171a2e922c, phi = n * weighted-position
  excess + k, was about 33x). Argument: e = I + excess, I = inversions of the token order read clockwise from token
  1 (zeros skipped), excess = sum over tokens of ((p - pos1) mod n) - m(m-1)/2. e = 0 exactly when
  csorted, L and R leave e unchanged, and X at an improving cell (token t > 1 at position 1 with a
  zero or a larger token at position 0; token 1 never moved) lowers e by exactly 1. k = shorter
  circular distance to the nearest improving cell: one rotation lowers k by 1, and after X the new
  k is at most floor(n/2). So phi = (floor(n/2) + 1) * e + k descends; csorted uses rot_dist.
- Slack: the multiplier floor(n/2) + 1 pays a half-circle trip per unit of e, but e alone is near T
  (about 42 vs 48 at m8r3), so real paths spend about one rotation per X. Lowering the multiplier
  to floor(n/2) fails descent (round 3: 12 to 866 failing states per graph). External evidence for
  one rotation per X (pure LRX, r = 1; Antiufeev arXiv:2601.08715 and an external audit, not proved
  here): word length = #X + #rotations; reversing j adjacent entries costs j(j-1)-1, one X plus one
  single shift per inverted pair (carry pattern X L X L ... or R X R X ...).
- The amortised idea (pay little per unit of e while a carry continues, pay the long jump of k only
  when a carry ends) is what produced the round 4 gain, with u = number of improving cells + 1.
  Check descent on the failing examples the evaluator returns.
- Size limit 80 expression nodes; 6ff08 uses 79 (two round 4 proposals were rejected at > 80).
  Savings used there: fold the constant m(m-1)/2 into the sum as "- tgt" per token, and write
  m + 1 - 2t as m - (t + tgt). Built-ins: cdes, cinv (min over rotations of inversions), inv
  (inversions read from position 0), token variables tgt, gap_next and zeros_next.
- Keep phi integer-valued and keep the csorted -> rot_dist branch. One state without a descending
  neighbour on any sanity graph stops the evaluation.
