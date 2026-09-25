# First adaevolve proposer prompt, seed 1 (bound-m-c3-260926)

Captured offline through the mock (no provider call). Only development families (m = 9, 10) appear; the validation (m = 11) and holdout (m = 11, 12) sets are never loaded by an engine.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `f6e0102e244899047d69d956e5be1f72833555c0066169d32fa094cdbce32ce4`
- Message roles: ['system', 'user']
- Client request fields: model `gemini-3.8-flash`, max_tokens `16384`, reasoning_effort `low`
- Captured from: `capture-adaevolve-s1/request-0001.json`
- A live run is marked FIRST_PROMPT_MISMATCH and fails if its first solution request in the run's ledger receipts hashes differently (SkyDiscover has no pre-send hook).

## Message 1: system

``````text
Find a uniform construction of LRX sorting words whose length is provably bounded for a whole family of states. L rotates the vector left (first entry to the end), R rotates right, X swaps the first two entries. A family (a, S) is a label order a (a permutation of 1..m) and a set S of k nonempty gaps (gap g lies after the first g labels; g = 0 leading, g = m trailing); its states have u_j >= 1 zeros in the j-th gap of S; the unit base has one zero per gap. The candidate source must define certify(family) -> {'tree': NODE} (a plain {'words': [...]} is one leaf with unit origins). NODE is a split {'j': axis, 't': 1..12, 'le': NODE, 'ge': NODE} (u_j <= t goes to le, u_j >= t+1 to ge; the root box is [1, inf)^k) or a leaf {'words': [...], 'origins': [o_0..o_{k-1}], 'picks'?: [...]}: depth <= 6, <= 32 leaves, 1..32 words per leaf, <= 4000 letters per word, <= 256000 in all, o_j <= the leaf's lower corner l_j. A leaf's words are literal words on the REFINED base, where block j holds o_j zeros (picks[j], default 0, is the zero of block j that stretches); each must sort it to (1..m, 0..0) and never swap two zeros. The trusted evaluator prices each word with the research group's Lemma 1 (exact, any m): B = (number of X) + sum over segments of |net rotation|, beta_j = 2 * (X letters touching the stretched zero of block j) + sum over segments of |signed crossings of it| (a segment ends at every X), and cost C(u) = B + sum_j beta_j (u_j - o_j) on the leaf. Per leaf with box [l_j, h_j] an exact LP over your words checks criterion (8): some mixture has Cbar(l) - T(l) + sum over bounded j of max(0, betabar_j - s)(h_j - l_j) < 1 and betabar_j <= s on every unbounded axis, with s = m - 2 and T(l) = m(m+1)/2 + (sum_j l_j - 1)(m-2). The family is CERTIFIED when every leaf passes; that proves d(v) <= T_m(n) for every state of the family. Refining the stretched block (origin o_j > 1 on a leaf far out on axis j) lowers the slope a word needs there. Each family gets 3 s of CPU (module import 1 s). Score per m: percentage certified (the worst m counts twice), plus small terms for valid output and a small worst leaf gap. Development families are m = 9 and 10, reversal-type orders oversampled; the holdout has unseen families and an unseen m, so the program must work for any m with no tables: string constants over L/R/X of 24+ characters, literal containers with more than 64 elements and bytes constants over 256 bytes are rejected. Stdlib only, at most 64 KiB. Do not read files, the network, or environment variables. Misses prove nothing.
``````

## Message 2: user

``````text
# Current Solution Information
- Main Metrics: 
- combined_score: 173.4449

Metrics:
  - screen_certified: 26.0000
  - screen_valid: 30.0000
  - screen_max_gap: 1.4375
  - full_certified: 283.0000
- Focus areas: - Solution is long (>500 chars); consider simplifying while preserving quality

# Program Generation History
## Previous Attempts

No previous attempts yet.



# Current Solution
# Current Solution

## PARENT SELECTION CONTEXT
This parent was selected through diversity-driven sampling to explore different regions.

### EXPLORATION GUIDANCE
- Consider alternative algorithmic approaches
- Don't be constrained by the parent's approach
- Look for fundamentally different algorithms or novel techniques
- Balance creativity with correctness

Your goal: Discover new approaches that might outperform current solutions.

## Program Information
combined_score: 173.4449
Score breakdown:
  - screen_certified: 26.0000
  - screen_valid: 30.0000
  - screen_max_gap: 1.4375
  - full_certified: 283.0000

```python
"""Refined-origin tree certifier (campaign 3 seed): campaign-2 AdaEvolve-s2 plus staircase trees.

certify(family) returns a bound-contract-3 tree for the unit base v of (a, S)
(one zero per nonempty gap; n = m + k; m = max(v), k = number of zeros).

Root leaf. The campaign-2 AdaEvolve-s2 finalist, unchanged, builds a pool of
lift-and-sweep words (every target rotation t, zero routings: all k! for
k <= 4, 2k dihedral ones otherwise; sweeps L, R, greedy, greedy_R, bounce_L,
bounce_R, two cursor starts), prices each by the Lemma 1 cost (B, beta) and
keeps 32 (coordinate minimizers, lower convex hulls of (B, beta_j), ray
scalarizations, softmax Frank-Wolfe). A float LP checks criterion (7) on these
words; if it passes, the program returns them as one unit-origin root leaf.

Staircase. Otherwise, for one axis j at a time (the zero with the largest
minimal slope first), it walks lower corners l = 1, 2, ...: the leaf at l uses
origin o_j = min(l, 3) (block j refined to o_j zero atoms, the first atom
stretched), the same lift-and-sweep generator on the refined base (no
zero-zero swap), prices with picks, a Pareto filter on (B, beta), and a float
LP for criterion (8), C(u) = B + beta.(u - o), T(l) = T_m(m + sum l). If the
unbounded leaf [l, inf) passes the tree closes; else the widest [l, h], h <= 12,
found by bisection becomes a leaf and l = h + 1. At most 7 leaves, 16 words per
leaf (LP support first). Everything stops at 2.3 s of process CPU; then the
root leaf is returned. The evaluator's exact LP decides every leaf.
"""

KEEP = 32


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, t, perm, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (t + v[p] - 1) % n
    for i in range(r):
        target[zeros[i]] = (t + m + perm[i]) % n

    lift_bases = []
    base1 = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    lift_bases.append(base1)
    if n % 2 == 0:
        base2 = [((target[p] - p + n // 2 - 1) % n) - (n // 2 - 1) for p in range(n)]
        if base2 != base1:
            lift_bases.append(base2)

    res = []
    for rem_base in lift_bases:
        q = sum(rem_base) // n
        if q == 0:
            if rem_base not in res:
                res.append(rem_base)
            continue
        for rev_tie in (False, True):
            rem = list(rem_base)
            order = sorted(range(n), key=lambda p: (rem[p], -p if rev_tie else p), reverse=q > 0)
            for p in order[:abs(q)]:
                rem[p] -= n if q > 0 else -n
            if rem not in res:
                res.append(rem)
    return res


def _sweep(v, rem, t, mode, c_start=0, limit=4000):
    n = len(v)
    a, rem = list(v), list(rem)
    out = []
    c = 0
    if c_start != 0:
        d = c_start % n
        out.append('L' * d if d <= n - d else 'R' * (n - d))
        c = c_start % n

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] or a[y]:
            out.append('X')
            a[x], a[y] = a[y], a[x]
        rem[x], rem[y] = ry + 1, rx - 1

    bounce_dir = 1 if mode == 'bounce_L' else -1
    bounce_steps = 0
    while any(rem) and len(out) < limit:
        if mode.startswith('greedy'):
            dirs = (1, -1) if mode == 'greedy' else (-1, 1)
            for dist in range(n):
                found = False
                for sgn in dirs:
                    pos = (c + sgn * dist) % n
                    if must_cross(pos):
                        out.append(('L' if sgn == 1 else 'R') * dist)
                        c = pos
                        found = True
                        break
                if found:
                    break
            else:
                return None
            cross(c)
            continue
        elif mode.startswith('bounce'):
            if must_cross(c):
                cross(c)
                if not any(rem):
                    break
            # Step in current bounce direction
            step_ch = 'L' if bounce_dir == 1 else 'R'
            out.append(step_ch)
            c = (c + bounce_dir) % n
            bounce_steps += 1
            if bounce_steps >= n - 1:
                bounce_dir = -bounce_dir
                bounce_steps = 0
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
    import itertools
    n, m = len(v), max(v)
    r = n - m
    words = {}

    if r <= 4:
        perms = list(itertools.permutations(range(r)))
    else:
        perms = [[(s + i) % r for i in range(r)] for s in range(r)] + [
            [(s + r - 1 - i) % r for i in range(r)] for s in range(r)
        ]

    for t in range(n):
        for perm in perms:
            for rem in _lifts(v, t, perm, m, r):
                for c_start in (0, t) if t != 0 else (0,):
                    for mode in ('L', 'R', 'greedy', 'greedy_R', 'bounce_L', 'bounce_R'):
                        w = _sweep(v, rem, t, mode, c_start=c_start)
                        if w is None:
                            continue
                        w = _reduce(w)
                        if w not in words and len(w) <= 4000:
                            cost = price(v, w)
                            if cost is not None:
                                words[w] = cost
    return words


def certify(family):
    v = family['unit_base']
    words = pool(v)
    if not words:
        return {'words': []}

    word_list = list(words.keys())
    m = max(v)
    k = sum(1 for x in v if x == 0)
    T = m * (m + 1) // 2 + (k - 1) * (m - 2)

    # Cost vectors for each word: [B - T, beta_0 - (m-2), ..., beta_{k-1} - (m-2)]
    # Target is to make all components <= 0 (or minimize max component)
    costs = []
    for w in word_list:
        B, beta = words[w]
        costs.append([B - T] + [b - (m - 2) for b in beta])

    n_words = len(word_list)
    dim = k + 1

    selected = set()

    # Always include top words for each coordinate
    for d in range(dim):
        best_idx = min(range(n_words), key=lambda i: (costs[i][d], max(costs[i])))
        selected.add(word_list[best_idx])

    import math

    # Convex Hull boundary & Pareto frontier extraction
    hull_indices = set()

    # 1. 2D Lower Convex Hull projections: (B vs beta_j) for each zero j
    for j in range(1, dim):
        pts = sorted(range(n_words), key=lambda i: (costs[i][0], costs[i][j]))
        # Andrew's monotone chain algorithm for lower hull
        lower = []
        for p in pts:
            while len(lower) >= 2:
                p1, p2 = lower[-2], lower[-1]
                # cross product (p2 - p1) x (p - p1)
                dx1, dy1 = costs[p2][0] - costs[p1][0], costs[p2][j] - costs[p1][j]
                dx2, dy2 = costs[p][0] - costs[p1][0], costs[p][j] - costs[p1][j]
                if dx1 * dy2 - dy1 * dx2 <= 0:
                    lower.pop()
                else:
                    break
            lower.append(p)
        for idx in lower:
            hull_indices.add(idx)

    # 2. Multi-angle scalarization scans across complementary trade-off rays
    for j in range(1, dim):
        for ratio in (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0):
            best_idx = min(range(n_words), key=lambda i: costs[i][0] + ratio * costs[i][j])
            hull_indices.add(best_idx)

    # 3. Softmax Frank-Wolfe to find complementary mixtures for minimax cost
    for alpha in (1.5, 3.0):
        for start_mode in ('min_max', 'min_b'):
            if start_mode == 'min_max':
                cur_idx = min(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
            else:
                cur_idx = min(range(n_words), key=lambda i: (costs[i][0], max(costs[i])))
            cur_vec = list(costs[cur_idx])
            hull_indices.add(cur_idx)
            for it in range(1, 40):
                mx = max(cur_vec)
                exps = [math.exp(min(50.0, alpha * (v - mx))) for v in cur_vec]
                tot = sum(exps)
                weights = [e / tot for e in exps]
                best_i = min(range(n_words), key=lambda i: sum(weights[d] * costs[i][d] for d in range(dim)))
                hull_indices.add(best_i)
                gamma = 2.0 / (it + 2)
                for d in range(dim):
                    cur_vec[d] = (1.0 - gamma) * cur_vec[d] + gamma * costs[best_i][d]

    # Coordinate minimizers
    for d in range(dim):
        hull_indices.add(min(range(n_words), key=lambda i: (costs[i][d], max(costs[i]))))

    # Prioritize vertices by minimax violation and lowest B
    ordered = sorted(hull_indices, key=lambda i: (max(costs[i]), costs[i][0], sum(costs[i])))
    selected_indices = list(ordered[:KEEP])

    # Fill remaining slots up to KEEP
    if len(selected_indices) < KEEP:
        by_max = sorted(range(n_words), key=lambda i: (max(costs[i]), costs[i][0]))
        for idx in by_max:
            if idx not in selected_indices:
                selected_indices.append(idx)
                if len(selected_indices) >= KEEP:
                    break

    res = [word_list[i] for i in selected_indices[:KEEP]]
    return {'words': res, 'note': 'sweep pool %d words, selected %d' % (len(words), len(res))}


# ---------------------------------------------------------------- campaign 3: tree certificates
# Everything below wraps the campaign-2 program above into the bound-contract-3 tree output.
# The words of every leaf come from the same lift-and-sweep machinery, run on a REFINED base
# (block j of the unit base holds o_j zero atoms); no table and no m-specific constant is used.

import time as _time

_certify_c2 = certify
_pool_c2 = pool
_POOLS = {}


def pool(v):
    """Memoized campaign-2 pool (the root leaf and the unit-origin staircase leaf share it)."""
    key = tuple(v)
    if key not in _POOLS:
        _POOLS[key] = _pool_c2(v)
    return _POOLS[key]

MAX_ORIGIN = 3      # largest refined origin o_j tried on the split axis
MAX_CUT = 12        # largest split threshold the contract allows
MAX_STEPS = 7       # leaves per staircase
LEAF_WORDS = 16     # words written per leaf (LP support first)
CPU_BUDGET = 2.3    # seconds of process CPU per family, measured from certify entry
EPS = 1e-9


def _budget(m, r):
    return m * (m + 1) // 2 + (r - 1) * (m - 2)


def _refine(v, origins):
    out, j = [], 0
    for x in v:
        if x:
            out.append(x)
        else:
            out.extend([0] * origins[j])
            j += 1
    return out


def _price_picks(v, word, picks):
    """Lemma 1 cost (B, beta) of word on a refined base v; picks[j] is the global index of the
    stretched zero atom of block j. None if the word does not sort v or swaps two zero atoms."""
    n = len(v)
    k = len(picks)
    blk = {p: j for j, p in enumerate(picks)}
    a, g = [], 0
    for x in v:
        if x:
            a.append(x)
        else:
            a.append(-1 - g)
            g += 1
    m = n - g
    A, q, d, cz, c = [0] * k, 0, 0, [0] * k, 0
    segs = []
    for ch in word:
        if ch == 'L':
            d += 1
            if a[c] < 0 and (-1 - a[c]) in blk:
                cz[blk[-1 - a[c]]] += 1
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            d -= 1
            if a[c] < 0 and (-1 - a[c]) in blk:
                cz[blk[-1 - a[c]]] -= 1
        else:
            c2 = (c + 1) % n
            x, y = a[c], a[c2]
            if x < 0 and y < 0:
                return None
            q += 1
            nxt = [0] * k
            if x < 0 and (-1 - x) in blk:
                cz[blk[-1 - x]] += 1
                A[blk[-1 - x]] += 1
            elif y < 0 and (-1 - y) in blk:
                A[blk[-1 - y]] += 1
                nxt[blk[-1 - y]] = -1
            segs.append((d, cz))
            d, cz = 0, nxt
            a[c], a[c2] = y, x
    segs.append((d, cz))
    fin = a[c:] + a[:c]
    if fin[:m] != list(range(1, m + 1)):
        return None
    B = q + sum(abs(s) for s, _ in segs)
    beta = [2 * A[i] + sum(abs(z[i]) for _, z in segs) for i in range(k)]
    return B, beta


def _sweep_words(v, deadline):
    """Every lift-and-sweep word of the campaign-2 pool for the (possibly refined) base v."""
    import itertools
    n, m = len(v), max(v)
    r = n - m
    if r <= 4:
        perms = list(itertools.permutations(range(r)))
    else:
        perms = [[(s + i) % r for i in range(r)] for s in range(r)] + [
            [(s + r - 1 - i) % r for i in range(r)] for s in range(r)]
    words = set()
    for t in range(n):
        if _time.process_time() > deadline:
            break
        for perm in perms:
            for rem in _lifts(v, t, perm, m, r):
                for c_start in (0, t) if t != 0 else (0,):
                    for mode in ('L', 'R', 'greedy', 'greedy_R', 'bounce_L', 'bounce_R'):
                        w = _sweep(v, rem, t, mode, c_start=c_start)
                        if w is not None:
                            w = _reduce(w)
                            if len(w) <= 4000:
                                words.add(w)
    return sorted(words, key=lambda w: (len(w), w))


def _pareto(priced):
    """[(word, B, beta)] -> the Pareto frontier on (B, beta), one shortest word per cost vector."""
    best = {}
    for w, B, beta in priced:
        key = (B,) + tuple(beta)
        if key not in best or (len(w), w) < (len(best[key]), best[key]):
            best[key] = w
    keys = sorted(best)
    keep = []
    for x in keys:
        if not any(all(p <= q for p, q in zip(y, x)) for y in keep):
            keep.append(x)
    return [(best[x], x[0], list(x[1:])) for x in keep]


def _simplex(A, b, c):
    """min c.x, A x = b, x >= 0 in floats, two phases, Bland's rule. -> (x, value) or None."""
    rows, cols = len(A), len(c)
    T = []
    for i in range(rows):
        s = -1.0 if b[i] < 0 else 1.0
        T.append([s * x for x in A[i]] + [1.0 if r == i else 0.0 for r in range(rows)] + [s * b[i]])
    basis = list(range(cols, cols + rows))

    def pivot(r, j):
        p = T[r][j]
        T[r] = [x / p for x in T[r]]
        for i in range(rows):
            if i != r and abs(T[i][j]) > 1e-15:
                f = T[i][j]
                T[i] = [x - f * y for x, y in zip(T[i], T[r])]
        basis[r] = j

    def run(cost, allowed):
        for _ in range(2000):
            enter = None
            for j in allowed:
                if j in basis:
                    continue
                if cost[j] - sum(cost[basis[i]] * T[i][j] for i in range(rows)) < -EPS:
                    enter = j
                    break
            if enter is None:
                return True
            cand = [i for i in range(rows) if T[i][enter] > EPS]
            if not cand:
                return False
            r = min(cand, key=lambda i: (T[i][-1] / T[i][enter], basis[i]))
            pivot(r, enter)
        return False

    if not run([0.0] * cols + [1.0] * rows, range(cols + rows)):
        return None
    if sum(T[i][-1] for i in range(rows) if basis[i] >= cols) > 1e-7:
        return None
    for r in range(rows):
        if basis[r] >= cols:
            j = next((j for j in range(cols) if abs(T[r][j]) > EPS and j not in basis), None)
            if j is not None:
                pivot(r, j)
    if not run(list(c) + [0.0] * rows, range(cols)):
        return None
    x = [0.0] * cols
    for i, j in enumerate(basis):
        if j < cols:
            x[j] = T[i][-1]
    return x, sum(ci * xi for ci, xi in zip(c, x))


def _leaf_lp(cols, origins, lo, hi, s, m):
    """Criterion (8) on the box prod [lo_j, hi_j] (hi_j None = unbounded) for the priced words
    cols = [(word, B, beta)] of the refined base with these origins. -> (passes, weights)."""
    k = len(lo)
    n = len(cols)
    bnd = [j for j in range(k) if hi[j] is not None]
    T = _budget(m, sum(lo))
    cost = [B + sum(b * (l - o) for b, l, o in zip(beta, lo, origins)) for _, B, beta in cols]
    A = []
    for j in range(k):
        A.append([beta[j] for _, _, beta in cols] + [-1.0 if bj == j else 0.0 for bj in bnd]
                 + [1.0 if i == j else 0.0 for i in range(k)])
    A.append([1.0] * n + [0.0] * (len(bnd) + k))
    c = cost + [hi[j] - lo[j] for j in bnd] + [0.0] * k
    out = _simplex(A, [float(s)] * k + [1.0], c)
    if out is None:
        return False, None
    x, val = out
    return val < T + 1 - 1e-6, x[:n]


def _leaf(cols, origins, weights):
    order = sorted(range(len(cols)), key=lambda i: (-weights[i], cols[i][1], i))
    words = [cols[i][0] for i in order if weights[i] > 1e-12]
    for i in order:
        if len(words) >= LEAF_WORDS:
            break
        if cols[i][0] not in words:
            words.append(cols[i][0])
    return {'words': words[:LEAF_WORDS], 'origins': list(origins)}


def _columns(v, origins, deadline, cache):
    key = tuple(origins)
    if key not in cache:
        ref = _refine(v, origins)
        picks = [sum(origins[:j]) for j in range(len(origins))]
        priced = []
        for w in _sweep_words(ref, deadline):
            p = _price_picks(ref, w, picks)
            if p is not None:
                priced.append((w, p[0], p[1]))
        cache[key] = _pareto(priced)
    return cache[key]


def _staircase(v, m, k, axis, deadline, cache):
    """Right comb of splits u_axis <= h; leaf at lower corner l uses origin min(l, MAX_ORIGIN) on axis."""
    s = m - 2
    leaves, l = [], 1
    while len(leaves) < MAX_STEPS and l <= MAX_CUT + 1 and _time.process_time() < deadline:
        origins = [1] * k
        origins[axis] = min(l, MAX_ORIGIN)
        cols = _columns(v, origins, deadline, cache)
        if not cols:
            return None
        lo = [1] * k
        lo[axis] = l
        ok, w = _leaf_lp(cols, origins, lo, [None] * k, s, m)
        if ok:
            leaves.append((_leaf(cols, origins, w), None))
            tree = leaves[-1][0]
            for node, h in reversed(leaves[:-1]):
                tree = {'j': axis, 't': h, 'le': node, 'ge': tree}
            return tree
        if len(leaves) + 1 >= MAX_STEPS or l > MAX_CUT:
            return None
        lo_h, hi_h, best = l, MAX_CUT, None
        while lo_h <= hi_h:  # criterion (8) gets harder as the box widens: bisect the widest passing h
            mid = (lo_h + hi_h) // 2
            hi = [None] * k
            hi[axis] = mid
            ok, w = _leaf_lp(cols, origins, lo, hi, s, m)
            if ok:
                best, lo_h = (mid, w), mid + 1
            else:
                hi_h = mid - 1
        if best is None:
            return None
        leaves.append((_leaf(cols, origins, best[1]), best[0]))
        l = best[0] + 1
    return None


def certify(family):
    start = _time.process_time()
    deadline = start + CPU_BUDGET
    out = _certify_c2(family)
    v = family['unit_base']
    m, k = max(v), sum(1 for x in v if x == 0)
    root = {'words': out['words'], 'origins': [1] * k}
    base = []
    for w in out['words']:
        p = price(v, w)
        if p is not None:
            base.append((w, p[0], p[1]))
    if not base or _leaf_lp(base, [1] * k, [1] * k, [None] * k, m - 2, m)[0]:
        return {'tree': root, 'note': out.get('note', '')}
    cache = {}
    unit = _pareto([(w, B, beta) for w, (B, beta) in pool(v).items()]) if _time.process_time() < deadline else []
    if unit:
        cache[tuple([1] * k)] = unit
    load = [min(beta[j] for _, _, beta in unit) if unit else 0 for j in range(k)]
    for axis in sorted(range(k), key=lambda j: (-load[j], j)):
        if _time.process_time() > deadline:
            break
        tree = _staircase(v, m, k, axis, deadline, cache)
        if tree is not None:
            return {'tree': tree, 'note': 'refined-origin staircase on axis %d' % axis}
    return {'tree': root, 'note': 'no staircase within budget; ' + out.get('note', '')}

```

## feedback_continued
  word 0 w=0.614 len=55 B=55 beta=[8, 1, 7] C(l)=55.0
  word 8 w=0.318 len=69 B=69 beta=[6, 11, 9] C(l)=69.0
  word 6 w=0.068 len=63 B=63 beta=[8, 9, 3] C(l)=63.0
  bound: on leaf 0: d(v) <= T_m(n) + floor((1) + 4/11*(sum over unbounded j of u_j - l_j))
Mechanism: each X that touches zero block j costs 2 on beta_j; each net rotation step across block j (per segment between X letters) costs 1.
Hint (group's m=8 proof, REVERSAL-OBSTACLE.md section 2): 34 of 4088 m=8 reversal-orbit families needed piecewise tree certificates split on block lengths.
A table-fed control closed the m=9 reversal 9..1 with zeros in gaps 0 and 4 by a staircase on axis 0: leaves u0 in [1,2] (origins (1,1)), [3,4] (origins (3,1)), u0 >= 5 (origins (5,1)), one word each.
Far out on an axis, refine its block (origin o_j > 1) so the stretched zero sits where words cross it less; near the corner, finite boxes tolerate slope above m-2.


## EVALUATOR FEEDBACK ON CURRENT PROGRAM
The evaluator analyzed cases where the current program failed and produced the following diagnostic feedback. Use this to make targeted improvements:

BOUND_PACKET_V3 (screen; development only; search signal, not proof)
this candidate m=9: certified 13/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 0.6, G 0.064; per k k2:0/1 k3:2/3 k4:1/1 k5:2/2 k6:2/2 k7:1/1 k8:2/2 k9:1/1 k10:2/2
this candidate m=10: certified 13/15, boundary 0, invalid 0, incomplete 0 (timeouts 0), W 1.44, G 0.163; per k k2:0/2 k3:2/2 k4:2/2 k5:1/1 k6:1/1 k7:2/2 k8:1/1 k9:2/2 k10:1/1 k11:1/1
this candidate combined 173.4449; best so far: screen 173.4449 (26/30 certified); full development 283/303 certified (m=9: 138, m=10: 145), worst gap 2.14
seed full development: m=9 138/153, m=10 145/150
- m10-mask528-labels9.8.7.6.5.4.2.3.1.10 (near_rev) m=10 k=2 mask=528 gaps=[4, 9] unit_base=[9, 8, 7, 6, 0, 5, 4, 2, 3, 1, 0, 10] T=63 s=8: NO_CERTIFICATE g=1.438; reversal orbit: no
  tree: 1 leaves, 0 pass
  worst leaf 0: box [1,inf] x [1,inf] origins [1, 1] T(l)=63 NO_CERTIFICATE gap 1.438 lhs 1.0 (needs < 1) slope excess 1.438
  word 0 w=0.688 len=59 B=59 beta=[3, 11] C(l)=59.0
  word 4 w=0.312 len=75 B=75 beta=[12, 6] C(l)=75.0
  bound: on leaf 0: d(v) <= T_m(n) + floor((1) + 23/16*(sum over unbounded j of u_j - l_j))
- m10-mask1025-labels10.9.8.7.6.5.4.3.2.1 (tight) m=10 k=2 mask=1025 gaps=[0, 10] unit_base=[0, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0] T=63 s=8: NO_CERTIFICATE g=1.0; reversal orbit: yes
  tree: 1 leaves, 0 pass
  worst leaf 0: box [1,inf] x [1,inf] origins [1, 1] T(l)=63 NO_CERTIFICATE gap 1.0 lhs 1.0 (needs < 1) slope excess 1.0
  word 0 w=1.0 len=64 B=64 beta=[9, 8] C(l)=64.0
  bound: on leaf 0: d(v) <= T_m(n) + floor((1) + 1*(sum over unbounded j of u_j - l_j))
- m9-mask656-labels432198765 (rev_rot) m=9 k=3 mask=656 gaps=[4, 7, 9] unit_base=[4, 3, 2, 1, 0, 9, 8, 7, 0, 6, 5, 0] T=59 s=7: NO_CERTIFICATE g=0.364; reversal orbit: yes
  tree: 1 leaves, 0 pass
  worst leaf 0: box [1,inf] x [1,inf] x [1,inf] origins [1, 1, 1] T(l)=59 NO_CERTIFICATE gap 0.364 lhs 1.0 (needs < 1) slope excess 0.364

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
