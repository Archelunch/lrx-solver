# First adaevolve proposer prompt (bound-m-260925, bound-contract-1)

This is the exact `messages` array the adaevolve arm sends to the local broker for its first program proposal on the seed, captured offline from a zero-provider run through the mock with the frozen development set. Only development families (m = 9, 10) appear; the holdout is never loaded.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `a0d78137c762596871b192211e2798e9456a33e965c1fa720e7cdbcf9a09aa7a`
- Message roles: ['system', 'user']
- Client request fields: model `gemini-3.8-flash`, max_tokens `8192`, reasoning_effort `None`
- Captured from: `run-adaevolve-a` (request-0001.json)
- A live run is marked FIRST_PROMPT_MISMATCH and fails if its first solution request in the arm's ledger receipts hashes differently (SkyDiscover has no pre-send hook).

## Message 1: system

``````text
Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of nonempty gaps (gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have l_j >= 1 zeros in the j-th gap of S, and its unit base has exactly one zero per gap. The candidate source must define certify(family) -> {'words': [...]} returning 1..32 words over L, R, X (at most 4000 letters each) that sort the unit base to (1, ..., m, 0, ..., 0) and never swap two zeros; optional 'weights' (rational strings) and 'note' are only reported. The trusted evaluator prices each word with the research group's Lemma 1 (exact, the same for every m): a word stretches to every block length, |W(z)| <= B + sum_j beta_j z_j with z_j = l_j - 1, B = (number of X) + sum over segments of |net rotation|, beta_j = 2 * (X letters touching block j) + sum over segments of |signed crossings of block j|, where a segment ends at every X. It then solves an exact LP over your words: the family is CERTIFIED when some mixture has weighted B < T + 1 and every weighted beta_j <= m - 2, with T = m(m+1)/2 + (k-1)(m-2) and k = |S|. That proves d(v) <= T_m(n) for every state of the family at every number of zeros. The binding constraint is usually the slope: sweeps cross zero blocks too often. Each family gets 3 s of CPU (module import 1 s); exact LP or search over a few hundred candidate words per family fits. Score per m: percentage of families certified (the worst m counts twice), plus small terms for valid output and a small gap. Development families are m = 9 and 10, reversal-type orders oversampled; the holdout has unseen families and an unseen m, so the program must work for any m with no tables: string constants over L/R/X of 24+ characters, literal containers with more than 64 elements and bytes constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. Do not read files, the network, or environment variables. Misses prove nothing.
``````

## Message 2: user

``````text
# Current Solution Information
- Main Metrics: 
- combined_score: 26.7487

Metrics:
  - screen_certified: 6.0000
  - screen_valid: 30.0000
  - screen_max_gap: 6.0000
  - full_certified: 111.0000
- Focus areas: - Solution is long (>500 chars); consider simplifying while preserving quality

# Program Generation History
## Previous Attempts

No previous attempts yet.



# Current Solution
# Current Solution

## PARENT SELECTION CONTEXT
This parent was selected from the archive of top-performing programs.

### OPTIMIZATION GUIDANCE
- This solution works well, but meaningful improvements are still possible
- You may refine the existing approach OR introduce better algorithms
- Consider: algorithmic improvements, better data structures, efficient libraries
- Ensure correctness is maintained

Your goal: Improve upon this solution.

## Program Information
combined_score: 26.7487
Score breakdown:
  - screen_certified: 6.0000
  - screen_valid: 30.0000
  - screen_max_gap: 6.0000
  - full_certified: 111.0000

```python
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

## feedback_continued
  word 2 w=0.286 len=116 B=116 beta=[11, 12, 11, 8, 5, 4, 7, 10] = 2*A[4, 5, 3, 2, 1, 2, 3, 4] + rot[3, 2, 5, 4, 3, 0, 1, 2] same_sign=True
  word 9 w=0.143 len=115 B=115 beta=[6, 7, 7, 10, 13, 7, 4, 5] = 2*A[2, 3, 3, 4, 5, 2, 1, 2] + rot[2, 1, 1, 2, 3, 3, 2, 1] same_sign=True
  bound: d(v) <= T_m(n) + floor((22/7) + 1*(r-k))
- m10-mask528-labels9.8.7.6.5.4.2.3.1.10 (near_rev) m=10 k=2 mask=528 gaps=[4, 9] unit_base=[9, 8, 7, 6, 0, 5, 4, 2, 3, 1, 0, 10] T=63 s=8: NO_CERTIFICATE g=2.118
  gap-LP mixture: Bbar 64.0 vs T+1=64; weighted slopes (j:gap:slope:excess[*=tight]) 0:4:6.29:-1.71 1:9:10.12:2.12*
  word 8 w=0.529 len=56 B=56 beta=[3, 12] = 2*A[1, 4] + rot[1, 4] same_sign=True
  word 1 w=0.471 len=73 B=73 beta=[10, 8] = 2*A[4, 3] + rot[2, 2] same_sign=True
  word 12 w=0.0 len=57 B=57 beta=[3, 13] = 2*A[1, 4] + rot[1, 5] same_sign=True
  bound: d(v) <= T_m(n) + floor((1) + 36/17*(r-k))
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.


## EVALUATOR FEEDBACK ON CURRENT PROGRAM
The evaluator analyzed cases where the current program failed and produced the following diagnostic feedback. Use this to make targeted improvements:

BOUND_PACKET_V1 (screen; development only; search signal, not proof)
this candidate m=9: certified 1/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 6.0, G 1.504; per k k2:0/1 k3:0/3 k4:0/1 k5:0/2 k6:0/2 k7:1/1 k8:0/2 k9:0/1 k10:0/2
this candidate m=10: certified 5/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 3.14, G 0.961; per k k2:0/2 k3:2/2 k4:0/2 k5:1/1 k6:0/1 k7:1/2 k8:0/1 k9:1/2 k10:0/1 k11:0/1
this candidate combined 26.7487; best so far: screen 26.7487 (6/30 certified); full development 111/303 certified (m=9: 51, m=10: 60), worst gap 8.0
seed full development: m=9 51/153, m=10 60/150
- m9-mask895-labels987654321 (rev_rot) m=9 k=9 mask=895 gaps=[0, 1, 2, 3, 4, 5, 6, 8, 9] unit_base=[0, 9, 0, 8, 0, 7, 0, 6, 0, 5, 0, 4, 0, 3, 2, 0, 1, 0] T=101 s=7: NO_CERTIFICATE g=6.0
  gap-LP mixture: Bbar 103.0 vs T+1=102; weighted slopes (j:gap:slope:excess[*=tight]) 0:0:12.0:5.0* 1:1:9.0:2.0 2:2:6.0:-1.0 3:3:3.0:-4.0 4:4:0.0:-7.0 5:5:3.0:-4.0 6:6:6.0:-1.0 7:8:12.0:5.0* 8:9:11.0:4.0
  word 6 w=1.0 len=103 B=103 beta=[12, 9, 6, 3, 0, 3, 6, 12, 11] = 2*A[4, 3, 2, 1, 0, 1, 2, 4, 4] + rot[4, 3, 2, 1, 0, 1, 2, 4, 3] same_sign=True
  word 7 w=0.0 len=103 B=103 beta=[12, 9, 6, 3, 0, 3, 6, 12, 11] = 2*A[4, 3, 2, 1, 0, 1, 2, 4, 4] + rot[4, 3, 2, 1, 0, 1, 2, 4, 3] same_sign=True
  bound: d(v) <= T_m(n) + floor((2) + 5*(r-k))
- m10-mask1851-labels1.10.9.8.7.6.5.4.3.2 (refl) m=10 k=8 mask=1851 gaps=[0, 1, 3, 4, 5, 8, 9, 10] unit_base=[0, 1, 0, 10, 9, 0, 8, 0, 7, 0, 6, 5, 4, 0, 3, 0, 2, 0] T=111 s=8: NO_CERTIFICATE g=3.143
  gap-LP mixture: Bbar 114.14 vs T+1=112; weighted slopes (j:gap:slope:excess[*=tight]) 0:0:8.0:0.0 1:1:9.0:1.0* 2:3:6.43:-1.57 3:4:7.71:-0.29 4:5:9.0:1.0* 5:8:9.0:1.0* 6:9:7.71:-0.29 7:10:7.0:-1.0
  word 0 w=0.571 len=113 B=113 beta=[7, 8, 4, 7, 10, 12, 9, 6] = 2*A[2, 3, 1, 2, 3, 4, 3, 2] + rot[3, 2, 2, 3, 4, 4, 3, 2] same_sign=True

# Task
Suggest improvements to the program that will improve its COMBINED_SCORE.
The system maintains diversity across these dimensions: score, complexity.
Different solutions with similar combined_score but different features are valuable.

You MUST use the exact SEARCH/REPLACE diff format shown below to indicate changes:

<<<<<<< SEARCH
# Original code to find and replace (must match exactly)
=======
# New replacement code
>>>>>>> REPLACE

**CRITICAL**: You can suggest multiple changes. Each SEARCH section must EXACTLY match code in "# Current Solution" - copy it character-for-character, preserving all whitespace and indentation. Do NOT paraphrase or reformat.
Be thoughtful about your changes and explain your reasoning thoroughly.
Include a concise docstring at the start of functions describing the exact approach taken.

IMPORTANT: If an instruction header of "## IMPORTANT: ..." is given below the "# Current Solution", you MUST follow it. Otherwise, 
focus on targeted improvements of the program. 

- Time limit: Programs should complete execution within 900 seconds; otherwise, they will timeout.
``````
