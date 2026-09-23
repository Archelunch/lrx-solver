Insights file (edited by the orchestrator, read by live campaigns as starting guidance).
Train-side evidence only; held-out results are never copied here.
- Lead candidates/leads/49ab346cb44b2f1b.json ("anchor token 1 and pull token 2") is sound on all
  train graphs; worst m>=8 ratio value/T = 1.5625 (75 vs 48 at m8r3, binding; 76 vs 52 at m9r2,
  63 vs 42 at m8r2). The bubble baseline is ~3x T. Idea: insert tokens 2..m one by one into a
  growing contiguous circular block (token 1 fixed), seek the next token with the short rotation,
  walk it with two-move primitives (X then L, or R then X) tracked in r2/r3, on the XL walk finish
  with X when pred sits at position 1. Cuts so far: skip an L that the next rule undoes (R once,
  r0=k+1, or r0=k+2 if k+1 is already attached); when r0==2 and token 1 is at the front, XL or RX
  walks the suffix until 2 sits at position 1 (2d moves instead of 3d-1).
- Lineage: 1ea0a8de (2.06x) -> 4189a604 (1.83x) -> 26b3e8cd (1.63x) -> c01093d9 (1.56x) ->
  49ab346c (1.56x). Accepted cuts removed rotations or special-cased the start without changing
  the insertion order. In rounds 2-3 no proposal lowered m8r3 below 75; start patches keyed to one
  worst probe state lower only that graph. Local cuts of this scheme look exhausted.
- External structure (pure LRX, r = 1; Antiufeev arXiv:2601.08715 and an external audit of it,
  not proved here): the hardest element is a reflection of the circle. Its short words split the
  circle into two complementary arcs of about n/2 entries, reverse each arc separately and join
  them with 2 shifts. Inside an arc each inverted pair costs one X plus one single shift (carry
  pattern X L X L ... or R X R X ...; reversing j adjacent entries costs j(j-1)-1). Entries in
  different arcs never swap: they pass around the far side, so the X count is about n^2/4, not
  n(n-1)/2.
- Hypothesis (not measured): one insertion costs about 2k + (return distance) for a token carried
  k steps, and the one-ended order makes carried tokens cross tokens that a two-sided order would
  route around the other way, so the scheme may stay near 1.5-2x T. Orders to try: start the block
  at any token (not necessarily 1) and grow it at both ends, the next token being (first token of
  the block) - 1 placed before it or (last token) + 1 placed after it, whichever carry is shorter
  (one register per end); or sort two arcs separately and merge; or carry the zero block. Round 4:
  two proposals tried a two-sided order; one tied the parent, one scored -1776. A two-sided order
  probably needs a new controller built and tested on small graphs first, not an edit of this one.
- Controllers written from scratch usually loop (cycle) on small graphs. Every rule sequence must
  provably make progress: keep a register for the token being served, clear it when the token
  reaches its slot, and keep the "csorted -> short rotation" finishing rules.
