# First gepa proposer prompt (bound-m-260925, bound-contract-1)

This is the exact `messages` array the gepa arm sends to the local broker for its first program proposal on the seed, captured offline from a zero-provider run through the mock with the frozen development set. Only development families (m = 9, 10) appear; the holdout is never loaded.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `573d5559f747bfdee2d0885f6173aa181e2f076960b67e8094f044770f6b260c`
- Message roles: ['user']
- Client request fields: model `gemini-3.8-flash`, max_tokens `8192`, reasoning_effort `None`
- Captured from: `run-gepa-a` (request-0001.json)
- A live run halts before its first model request if these messages hash differently.

## Message 1: user

``````text
You are an expert optimization assistant. Your task is to analyze evaluation feedback and propose an improved version of a system component.

## Optimization Goal

Improve this Python certify(family) program (the seed builds a pool of cyclic-sweep sorting words: every target rotation, cyclic assignment of the zeros and sweep direction, prices each word by the Lemma 1 cost, and returns the 16 with the lowest (max slope, base)). Return the entire replacement Python source in one fenced code block, with no prose and no docstring longer than a few lines. Raise the number of certified families, first on the worst m, by constructing words whose slopes beta_j stay at most m-2 (fewer X letters touching each zero block, fewer rotation passes across it) and by choosing the returned word set well. Only development families are shown.

## Domain Context & Constraints

Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of nonempty gaps (gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have l_j >= 1 zeros in the j-th gap of S, and its unit base has exactly one zero per gap. The candidate source must define certify(family) -> {'words': [...]} returning 1..32 words over L, R, X (at most 4000 letters each) that sort the unit base to (1, ..., m, 0, ..., 0) and never swap two zeros; optional 'weights' (rational strings) and 'note' are only reported. The trusted evaluator prices each word with the research group's Lemma 1 (exact, the same for every m): a word stretches to every block length, |W(z)| <= B + sum_j beta_j z_j with z_j = l_j - 1, B = (number of X) + sum over segments of |net rotation|, beta_j = 2 * (X letters touching block j) + sum over segments of |signed crossings of block j|, where a segment ends at every X. It then solves an exact LP over your words: the family is CERTIFIED when some mixture has weighted B < T + 1 and every weighted beta_j <= m - 2, with T = m(m+1)/2 + (k-1)(m-2) and k = |S|. That proves d(v) <= T_m(n) for every state of the family at every number of zeros. The binding constraint is usually the slope: sweeps cross zero blocks too often. Each family gets 3 s of CPU (module import 1 s); exact LP or search over a few hundred candidate words per family fits. Score per m: percentage of families certified (the worst m counts twice), plus small terms for valid output and a small gap. Development families are m = 9 and 10, reversal-type orders oversampled; the holdout has unseen families and an unseen m, so the program must work for any m with no tables: string constants over L/R/X of 24+ characters, literal containers with more than 64 elements and bytes constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. Do not read files, the network, or environment variables. Misses prove nothing.

## Current Component

The component being optimized:

```
"""Cyclic-sweep family certifier, top 16 (control b16, campaign seed).

certify(family) returns up to 16 sorting words for the unit base of (a, S).
The unit base v has one zero per nonempty gap. L moves a cursor one cell
right, R one cell left, X swaps the cells under the cursor and its right
neighbor (on the vector: L rotates left, X swaps the first two entries).

Pool: for every target rotation t of the root on the ring, every cyclic
assignment of the interchangeable zeros to the zero slots, and every sweep mode
(L-wise, R-wise, greedy nearest), give each cell a displacement on the universal
cover and sweep, swapping an adjacent pair exactly when the pair must cross;
two zeros never swap (they exchange displacements for free). Each word is
priced by the Lemma 1 affine cost B + sum_j beta_j z_j that the evaluator uses:
B = swaps + sum over segments |net rotation|, beta_j = 2 A_j + sum over
segments |signed crossings of zero block j|, where a segment ends at every X
and A_j counts the X letters that touch block j. The evaluator certifies the
family when some mixture of the returned words has weighted B < T + 1 and every
weighted beta_j <= m - 2. This seed keeps the 16 words with the lowest
(max_j beta_j, B) and leaves the mixture to the evaluator's exact LP.
"""

KEEP = 16


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, shift, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (t + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, t, mode, limit=4000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] or a[y]:
            out.append('X')
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    while any(rem) and len(out) < limit:
        if mode == 'greedy':
            for dist in range(n):
                if must_cross((c + dist) % n):
                    out.append('L' * dist)
                    c = (c + dist) % n
                    break
                if must_cross((c - dist) % n):
                    out.append('R' * dist)
                    c = (c - dist) % n
                    break
            else:
                return None
            cross(c)
            continue
        if must_cross(c):
            cross(c)
            if not any(rem):
                break
        out.append(mode)
        c = (c + (1 if mode == 'L' else -1)) % n
    if any(rem):
        return None
    d = (t - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def price(v, word):
    """Lemma 1 affine cost (B, beta) of word on the unit base v, or None if it does not
    sort v or swaps two zeros. Block j is the j-th zero of v (one zero per block)."""
    n, k = len(v), sum(1 for x in v if x == 0)
    a, j = [], 0
    for x in v:
        if x:
            a.append(x)
        else:
            j += 1
            a.append(-j)  # zero of block j-1
    segs, A, q, d, cz, c = [], [0] * k, 0, 0, [0] * k, 0
    for ch in word:
        if ch == 'L':
            d += 1
            if a[c] < 0:
                cz[-a[c] - 1] += 1
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            if a[c] < 0:
                cz[-a[c] - 1] -= 1
        else:
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x < 0 and y < 0:
                return None
            q += 1
            nxt = [0] * k
            if x < 0:
                cz[-x - 1] += 1
                A[-x - 1] += 1
            elif y < 0:
                A[-y - 1] += 1
                nxt[-y - 1] = -1
            segs.append((d, cz))
            d, cz = 0, nxt
            a[c], a[c2] = y, x
    segs.append((d, cz))
    fin = a[c:] + a[:c]
    m = n - k
    if fin[:m] != list(range(1, m + 1)):
        return None
    B = q + sum(abs(s) for s, _ in segs)
    beta = [2 * A[i] + sum(abs(z[i]) for _, z in segs) for i in range(k)]
    return B, beta


def pool(v):
    """{word: (B, beta)} over all sweep variants that sort v with no zero-zero swap."""
    n, m = len(v), max(v)
    r = n - m
    words = {}
    for t in range(n):
        for shift in range(r):
            rem = _lifts(v, t, shift, m, r)
            for mode in ('L', 'R', 'greedy'):
                w = _sweep(v, rem, t, mode)
                if w is None:
                    continue
                w = _reduce(w)
                if w not in words and len(w) <= 4000:
                    cost = price(v, w)
                    if cost is not None:
                        words[w] = cost
    return words


def certify(family):
    words = pool(family['unit_base'])
    ranked = sorted(words, key=lambda w: (max(words[w][1]), words[w][0], len(w), w))
    return {'words': ranked[:KEEP], 'note': 'sweep pool %d words, top %d by (max slope, base)'
            % (len(words), min(KEEP, len(words)))}

```

## Evaluation Results

Performance data from evaluating the current component across test cases:

```
# Example 1
## family_id
m9-mask68-labels219876543

## certified
0

## valid
1

## gap
3

## feedback
BOUND_PACKET_V1 (family m9-mask68-labels219876543; development only; search signal, not proof)
this candidate m=9: certified 0/1, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 3.0, G 3.0; per k k2:0/1
this family: per-family score 0.1250 (1 certified, 0.5/(1+g) valid miss, 0 invalid); best so far: screen 26.7487 (6/30 certified); full development 111/303 certified (m=9: 51, m=10: 60), worst gap 8.0
seed full development: m=9 51/153, m=10 60/150
- m9-mask68-labels219876543 (tight) m=9 k=2 mask=68 gaps=[2, 6] unit_base=[2, 1, 0, 9, 8, 7, 6, 0, 5, 4, 3] T=52 s=7: NO_CERTIFICATE g=3.0
  gap-LP mixture: Bbar 53.0 vs T+1=53; weighted slopes (j:gap:slope:excess[*=tight]) 0:2:10.0:3.0* 1:6:7.0:0.0
  word 7 w=0.5 len=50 B=50 beta=[11, 3] = 2*A[4, 1] + rot[3, 1] same_sign=True
  word 9 w=0.5 len=56 B=56 beta=[9, 11] = 2*A[4, 4] + rot[1, 3] same_sign=True
  word 13 w=0.0 len=48 B=48 beta=[13, 1] = 2*A[4, 0] + rot[5, 1] same_sign=True
  word 14 w=0.0 len=50 B=50 beta=[13, 1] = 2*A[5, 0] + rot[3, 1] same_sign=True
  word 8 w=0.0 len=52 B=52 beta=[11, 5] = 2*A[4, 2] + rot[3, 1] same_sign=True
  word 15 w=0.0 len=54 B=54 beta=[13, 7] = 2*A[5, 3] + rot[3, 1] same_sign=True
  bound: d(v) <= T_m(n) + floor((1) + 3*(r-k))
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.



# Example 2
## family_id
m9-mask944-labels532198764

## certified
0

## valid
1

## gap
16/9

## feedback
BOUND_PACKET_V1 (family m9-mask944-labels532198764; development only; search signal, not proof)
this candidate m=9: certified 0/1, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 1.78, G 1.778; per k k5:0/1
this family: per-family score 0.1800 (1 certified, 0.5/(1+g) valid miss, 0 invalid); best so far: screen 26.7487 (6/30 certified); full development 111/303 certified (m=9: 51, m=10: 60), worst gap 8.0
seed full development: m=9 51/153, m=10 60/150
- m9-mask944-labels532198764 (near_rev) m=9 k=5 mask=944 gaps=[4, 5, 7, 8, 9] unit_base=[5, 3, 2, 1, 0, 9, 0, 8, 7, 0, 6, 0, 4, 0] T=73 s=7: NO_CERTIFICATE g=1.778
  gap-LP mixture: Bbar 74.0 vs T+1=74; weighted slopes (j:gap:slope:excess[*=tight]) 0:4:8.78:1.78* 1:5:7.0:0.0 2:7:3.44:-3.56 3:8:3.22:-3.78 4:9:6.22:-0.78
  word 0 w=0.611 len=81 B=81 beta=[8, 7, 5, 4, 7] = 2*A[4, 3, 1, 0, 1] + rot[0, 1, 3, 4, 5] same_sign=True
  word 3 w=0.389 len=63 B=63 beta=[10, 7, 1, 2, 5] = 2*A[3, 2, 0, 1, 2] + rot[4, 3, 1, 0, 1] same_sign=True
  word 11 w=0.0 len=61 B=61 beta=[12, 9, 3, 0, 3] = 2*A[4, 3, 1, 0, 1] + rot[4, 3, 1, 0, 1] same_sign=True
  word 6 w=0.0 len=63 B=63 beta=[11, 8, 2, 3, 4] = 2*A[3, 2, 0, 1, 2] + rot[5, 4, 2, 1, 0] same_sign=True
  word 12 w=0.0 len=67 B=67 beta=[12, 9, 5, 2, 3] = 2*A[4, 3, 1, 0, 1] + rot[4, 3, 3, 2, 1] same_sign=True
  word 13 w=0.0 len=67 B=67 beta=[12, 9, 3, 4, 7] = 2*A[4, 3, 1, 2, 3] + rot[4, 3, 1, 0, 1] same_sign=True
  bound: d(v) <= T_m(n) + floor((1) + 16/9*(r-k))
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.



# Example 3
## family_id
m9-mask509-labels981364275

## certified
1

## valid
1

## gap
0

## feedback
BOUND_PACKET_V1 (family m9-mask509-labels981364275; development only; search signal, not proof)
this candidate m=9: certified 1/1, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 0.0, G 0.0; per k k8:1/1
this family: per-family score 1.0000 (1 certified, 0.5/(1+g) valid miss, 0 invalid); best so far: screen 26.7487 (6/30 certified); full development 111/303 certified (m=9: 51, m=10: 60), worst gap 8.0
seed full development: m=9 51/153, m=10 60/150
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.


```

## Your Task

Analyze the evaluation results systematically:

- **Goal alignment**: How well does the current component achieve the stated optimization goal?
- **Failure patterns**: What specific errors, edge cases, or failure modes appear in the evaluation data?
- **Success patterns**: What behaviors or approaches worked well and should be preserved?
- **Root causes**: What underlying issues explain the observed failures?
- **Constraint compliance**: Does the component satisfy all requirements from the domain context?

Based on your analysis, propose an improved version that:
1. Addresses the identified failure patterns and root causes
2. Preserves successful behaviors from the current version
3. Makes meaningful improvements rather than superficial changes
4. Adheres to all constraints and requirements from the domain context

## Output Format

Provide ONLY the improved version within ``` blocks. The output must be a complete, 
drop-in replacement for the current component (whether it's a prompt, configuration, 
code, or any other parameter type).
Do not include explanations, commentary, or markdown outside the ``` blocks.
``````
