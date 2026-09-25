# First gepa prompts, seed 1 (sort-m9-v3-260925)

Captured offline through the mock (no provider call) with the frozen development set; only development states appear. The solution request is hashed with any appended diagnosis replaced by `<DIAGNOSIS>`.

## solution request: `cf467ac3114647152c13c331661f8405866e184fda170765d600176f26d90d27` (from smoke-fix3-gepa-s1/request-0001.json)

### Message 1: user

``````text
You are an expert optimization assistant. Your task is to analyze evaluation feedback and propose an improved version of a system component.

## Optimization Goal

Improve this constructive Python sort_word(v) program (the seed is a cyclic-sweep sorter: it chooses a target rotation and a cyclic assignment of the interchangeable zeros, gives each entry a displacement on the universal cover, and sweeps the window swapping pairs that must cross). Return the entire replacement Python source in one fenced code block, with no prose and no docstring longer than a few lines. Raise the within-budget rate, first on the worst r, without search: each state has 0.2 s of CPU. Only development states are shown.

## Domain Context & Constraints

Find a constructive, uniform LRX sorting procedure. Goal: an algorithm that is uniform in r (and ideally in m) and provably stays within the budget T_m(n) = m(m+1)/2 + (r-1)(m-2) (45 + 7(r-1) at m=9), with a route whose length can be bounded by an argument. Useful ingredients: sweep strategies that use zero blocks as buffers, comparison-transfer routes that carry one label through a block, cycle-based service of labels in cyclic order, choosing the final rotation. The candidate source must define sort_word(v) -> str. v is a list of length n = m + r holding labels 1..m once (m = max(v)) and r >= 1 zeros; return a word over L, R, X that sorts v to (1, 2, ..., m, 0, ..., 0). L rotates the vector left (the first entry moves to the end), R rotates it right, and X swaps the first two entries. The trusted evaluator replays the word literally. Each call gets 0.2 s of CPU time (and module import 0.5 s); any state-space search (BFS, bidirectional BFS, IDA*, beam or A* search over vectors, or caching such search across calls) times out on almost every state, and a timeout counts as an unsorted state. Build the word directly from the structure of v. Score: fraction of development states sorted within T (primary), plus 0.5 times the worst per-r within-budget rate (so the program must work for every r, not only small r), plus a small term for low mean excess over the exact distance, minus the fraction not sorted. Stdlib only, at most 64 KiB, at most 1000 letters per word. Development states are m=9, r=1..5; the holdout has unseen states and unseen (m, r), so the program must work for any m and r. Misses prove nothing. Do not read files, the network, or environment variables. Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.

## Current Component

The component being optimized:

```
"""Heuristic LRX sorter (control b): cyclic bubble sweeps with zero blocks as buffers.

The vector is a ring with a moving window: L/R move the window, X swaps the two
ring cells under it. The target is any rotation k of the root on the ring, with
the window finally on label 1. For each k and each cyclic assignment of the
(interchangeable) zeros to the zero slots, every element gets an integer
displacement on the universal cover (shortest way round, adjusted so the sum is
zero). The window then sweeps and swaps an adjacent pair exactly when the pair
must cross on the cover. Two zeros never swap: they exchange displacements for
free, so zero blocks act as buffers. Sweeps run L-wise, R-wise, or greedy to
the nearest pair that must cross. The shortest word over all choices is freely
reduced (LR, RL, XX), replayed, and returned; control (a) is the fallback.
"""


def _replay(v, word):
    a = list(v)
    for ch in word:
        if ch == 'L':
            a.append(a.pop(0))
        elif ch == 'R':
            a.insert(0, a.pop())
        else:
            a[0], a[1] = a[1], a[0]
    return a


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, k, shift, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (k + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (k + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, k, mode, limit=2000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] == 0 and a[y] == 0:
            rem[x], rem[y] = ry + 1, rx - 1
            return
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
        if mode == 'L':
            out.append('L')
            c = (c + 1) % n
        else:
            out.append('R')
            c = (c - 1) % n
    if any(rem):
        return None
    d = (k - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def _naive(v):
    a = list(v)
    n, m = len(a), max(a)
    key = [x if x else m + 1 for x in a]
    out, c, end = [], 0, n - 1
    while end > 0:
        last = 0
        for i in range(end):
            if key[i] > key[i + 1]:
                k = (i - c) % n
                out.append(('L' * k if k <= n - k else 'R' * (n - k)) + 'X')
                c = i
                key[i], key[i + 1] = key[i + 1], key[i]
                last = i
        end = last
    k = (-c) % n
    out.append('L' * k if k <= n - k else 'R' * (n - k))
    return ''.join(out)


def sort_word(v):
    v = list(v)
    n, m = len(v), max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    best = None
    for k in range(n):
        for shift in range(max(1, r)):
            rem = _lifts(v, k, shift, m, r) if r else None
            if rem is None:
                continue
            for mode in ('L', 'R', 'greedy'):
                w = _sweep(v, rem, k, mode)
                if w is not None:
                    w = _reduce(w)
                    if (best is None or len(w) < len(best)) and _replay(v, w) == goal:
                        best = w
    return best if best is not None else _naive(v)

```

## Evaluation Results

Performance data from evaluating the current component across test cases:

```
# Example 1
## instance
r5-s5

## r
5

## d_range
### Item 1
68

### Item 2
70

## within
37

## states
50

## invalid
0

## timeouts
0

## mean_excess
3.0

## seed_within
37

## seed_mean_excess
3.0

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r5-s5 (d 68..70), 50 states.
this candidate: within budget 37/50, worst r m9r5 at 0.740, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 3.000, max excess 6; instance score 0.8025; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r5 37/50 t0 e3.0
seed per (m,r) within/states, timeouts, mean excess: m9r5 37/50 t0 e3.0
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r5-104085652 v=(2, 3, 1, 0, 0, 0, 0, 9, 7, 8, 6, 0, 4, 5) r=5 T=73 d=69 OVER_BUDGET len=75
  word: LXLXLXRRXLXRRXLXLXRRRXLXLXLXLXLLLXLXLXLXRXRXRXLXLXRRRXLXLXLXLLLLXLXLXLXLXRR
  leaves every shortest path at step 5 (d 65 -> 66); T unreachable after step 32
  aligned optimal: LXLXRXRXRXLXLXLXLXLLLLXLXRRXLXLXLXRXRXRXRXLXLXLXLLLLXLXLXLXLXRXRXRXLX
- m9r5-100853423 v=(5, 1, 0, 4, 3, 0, 0, 0, 0, 9, 8, 7, 6, 2) r=5 T=73 d=70 OVER_BUDGET len=74
  word: XLXLXLXRXRRXRXLXRRXLXLXLXLXLXLLLLLXLXLXRXRXLXRRXLXLXRRRXLXLXRRRXLXLXLLLLLL
  leaves every shortest path at step 15 (d 56 -> 57); T unreachable after step 44
  aligned optimal: XLXLXLXRXRRXRXRRRRRXLXLXLXRRRXRXLXLXLXRRXRXRXLXLXLXRXRXRXRRXRXRXRXRXLX
- m9r5-108074006 v=(3, 2, 1, 0, 0, 9, 0, 8, 0, 6, 7, 5, 4, 0) r=5 T=73 d=70 OVER_BUDGET len=74
  word: LXLXLXLXLXLLXLXLXLXLXRXRXLXRRXLXRRRXRRRXRXRXLXLXLXLXRRRRRRXLXRRXRXRXRXRXRR
  leaves every shortest path at step 33 (d 38 -> 39); T unreachable after step 34
  aligned optimal: LXLXLXLXLXLLXLXLXLXLXRXRXLXRRXLXLLLLXLLXLXLXLXRRXRXRXRRXRXRXRXRXRRXRXL
- m9r5-216187103 v=(5, 3, 2, 0, 1, 0, 0, 6, 0, 0, 9, 8, 7, 4) r=5 T=73 d=70 OVER_BUDGET len=74
  word: XRXRXLXLXLLXLXLXLXLLXLXLLXLXLXLXLXLLLXLXLLXLXRRXLXLLLLXLXLXLXRRRRXLXLXRRRR
  leaves every shortest path at step 11 (d 60 -> 61); T unreachable after step 35
  aligned optimal: XRXRXLXLXLXRRRRXLXLXLXLXLLLLLXRXRXLXLXLXLXLXRXRXRXRXRRXLXRRXRXRRXRXRXR



# Example 2
## instance
r3-s6

## r
3

## d_range
### Item 1
56

### Item 2
59

## within
24

## states
50

## invalid
0

## timeouts
0

## mean_excess
1.96

## seed_within
24

## seed_mean_excess
1.96

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r3-s6 (d 56..59), 50 states.
this candidate: within budget 24/50, worst r m9r3 at 0.480, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 1.960, max excess 4; instance score 0.5645; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r3 24/50 t0 e1.96
seed per (m,r) within/states, timeouts, mean excess: m9r3 24/50 t0 e1.96
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r3-28554079 v=(5, 4, 3, 2, 1, 0, 0, 0, 7, 9, 8, 6) r=3 T=59 d=58 OVER_BUDGET len=62
  word: LXLXLXLXLXLXLLLXLXLXRXRXLXRRXLXLLLLXLXLXLXLXRRRXLXLXRRRXLXLXLX
  leaves every shortest path at step 11 (d 48 -> 49); T unreachable after step 11
  aligned optimal: LXLXLXLXLXRRXRXRXLXLXLXRXRXRRRRXRXLXLXRXRRXLXRXRRXRXRXRXLX
- m9r3-5443199 v=(1, 0, 0, 0, 9, 8, 7, 6, 5, 2, 4, 3) r=3 T=59 d=58 OVER_BUDGET len=62
  word: XLXLXLLXLXLXLXRXRXLXRRXLXLXLLLLXLXLXLXLXRRRRXLXLXLXRRRRXLXLXLX
  leaves every shortest path at step 7 (d 52 -> 53); T unreachable after step 7
  aligned optimal: XLXLXLXLXRRXLXRRXLXRRXLXRXRRRRXRXLXLXRXRRXLXLXLXLXRXRXRXRR
- m9r3-59202214 v=(0, 0, 9, 8, 7, 6, 5, 4, 1, 3, 2, 0) r=3 T=59 d=58 OVER_BUDGET len=62
  word: LXRXRXRXLXLXLXLLXLXLXLXRXRXLXRRXLXLXLLLLXLXLXLXLXRRRRRXLXLXLXL
  leaves every shortest path at step 16 (d 43 -> 44); T unreachable after step 16
  aligned optimal: LXRXRXRXLXLXLXLXRXRXRXRXRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRRX
- m9r3-7257571 v=(2, 1, 0, 0, 8, 0, 7, 9, 6, 5, 4, 3) r=3 T=59 d=58 OVER_BUDGET len=62
  word: XLXLXRRXLXRRXLXLXLXLLLXLXLXLXRXRXLXRRXLXRRXLXLXLLLLXLXLXLXLXRR
  leaves every shortest path at step 6 (d 53 -> 54); T unreachable after step 6
  aligned optimal: XLXLXLXLXRRXRXRXRRRRXLXRXRXLXLXLXRXRXRXRXLXLXLXLLXLLXLXLXL



# Example 3
## instance
r2-s6

## r
2

## d_range
### Item 1
49

### Item 2
52

## within
39

## states
50

## invalid
0

## timeouts
0

## mean_excess
1.86

## seed_within
39

## seed_mean_excess
1.86

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r2-s6 (d 49..52), 50 states.
this candidate: within budget 39/50, worst r m9r2 at 0.780, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 1.860, max excess 4; instance score 0.8674; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r2 39/50 t0 e1.86
seed per (m,r) within/states, timeouts, mean excess: m9r2 39/50 t0 e1.86
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r2-1995836 v=(2, 1, 0, 0, 8, 9, 7, 6, 5, 4, 3) r=2 T=52 d=50 OVER_BUDGET len=54
  word: XLXLXRRXLXRRXLXLXLXLLLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRR
  leaves every shortest path at step 6 (d 45 -> 46); T unreachable after step 7
  aligned optimal: XLXLXLXRXRXRXRRRRXLXRXRXLXLXLXRXRXRXRRXRXRXRXLXLXL
- m9r2-19958387 v=(0, 0, 9, 7, 8, 6, 5, 4, 3, 2, 1) r=2 T=52 d=50 OVER_BUDGET len=54
  word: LXRXRXLXLXLLLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRRRRXLXLXLX
  leaves every shortest path at step 1 (d 50 -> 50); T unreachable after step 25
  aligned optimal: RXRRXLXRXRXRRRXRXRXLXLXLXRXRXRXRRXRXRXRXLXLXLXRXRX
- m9r2-3830396 v=(3, 2, 1, 0, 0, 8, 9, 7, 6, 5, 4) r=2 T=52 d=50 OVER_BUDGET len=54
  word: XLXRXRXLXLXLLLXLXLXLXRXRXLXRRXLXRRXLXLXLXLLLXLXLXLXRRR
  leaves every shortest path at step 4 (d 47 -> 47); T unreachable after step 13
  aligned optimal: XLXLXRXRXRRRRXRXLXLXLXRRXRXRXLXLXLXRXRXRXRRXRXRXLX
- m9r2-15920487 v=(9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0) r=2 T=52 d=50 OVER_BUDGET len=53
  word: LXLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRXRXRXLXLXRRRXLXLXLX
  leaves every shortest path at step 5 (d 46 -> 46); T unreachable after step 15
  aligned optimal: LXLXRXRXLXLXLXRXRXRXRRRXRXRXRXLXLXLXLXRXRXRXLXLXRX
- m9r2-17758003 v=(0, 9, 8, 7, 6, 5, 4, 2, 3, 1, 0) r=2 T=52 d=50 OVER_BUDGET len=53
  word: XLXLXRXRXLXRRXLXLXLLLXLXLXLXLLXLXLXLXLXLLXLXLXRRXLXRR
  leaves every shortest path at step 12 (d 39 -> 39); T unreachable after step 30
  aligned optimal: XLXLXRXRXLXLLXRXRXRXRXLXLXLXLLLLXLXRRXLXLXLXRXRXRX


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

Reviewer diagnosis (separate model; untrusted advice):
<DIAGNOSIS>
``````

## diagnosis request: `bb85de5c5b4b2c8ad609bddac3080be826d323022694c3f0b34f04ac20217e71` (from smoke-fix3-gepa-s1/request-0001.json)

### Message 1: system

``````text
Diagnose why the program fails on the listed states and propose concrete changes. Do not write code.
``````

### Message 2: user

``````text
You are an expert optimization assistant. Your task is to analyze evaluation feedback and propose an improved version of a system component.

## Optimization Goal

Improve this constructive Python sort_word(v) program (the seed is a cyclic-sweep sorter: it chooses a target rotation and a cyclic assignment of the interchangeable zeros, gives each entry a displacement on the universal cover, and sweeps the window swapping pairs that must cross). Return the entire replacement Python source in one fenced code block, with no prose and no docstring longer than a few lines. Raise the within-budget rate, first on the worst r, without search: each state has 0.2 s of CPU. Only development states are shown.

## Domain Context & Constraints

Find a constructive, uniform LRX sorting procedure. Goal: an algorithm that is uniform in r (and ideally in m) and provably stays within the budget T_m(n) = m(m+1)/2 + (r-1)(m-2) (45 + 7(r-1) at m=9), with a route whose length can be bounded by an argument. Useful ingredients: sweep strategies that use zero blocks as buffers, comparison-transfer routes that carry one label through a block, cycle-based service of labels in cyclic order, choosing the final rotation. The candidate source must define sort_word(v) -> str. v is a list of length n = m + r holding labels 1..m once (m = max(v)) and r >= 1 zeros; return a word over L, R, X that sorts v to (1, 2, ..., m, 0, ..., 0). L rotates the vector left (the first entry moves to the end), R rotates it right, and X swaps the first two entries. The trusted evaluator replays the word literally. Each call gets 0.2 s of CPU time (and module import 0.5 s); any state-space search (BFS, bidirectional BFS, IDA*, beam or A* search over vectors, or caching such search across calls) times out on almost every state, and a timeout counts as an unsorted state. Build the word directly from the structure of v. Score: fraction of development states sorted within T (primary), plus 0.5 times the worst per-r within-budget rate (so the program must work for every r, not only small r), plus a small term for low mean excess over the exact distance, minus the fraction not sorted. Stdlib only, at most 64 KiB, at most 1000 letters per word. Development states are m=9, r=1..5; the holdout has unseen states and unseen (m, r), so the program must work for any m and r. Misses prove nothing. Do not read files, the network, or environment variables. Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.

## Current Component

The component being optimized:

```
"""Heuristic LRX sorter (control b): cyclic bubble sweeps with zero blocks as buffers.

The vector is a ring with a moving window: L/R move the window, X swaps the two
ring cells under it. The target is any rotation k of the root on the ring, with
the window finally on label 1. For each k and each cyclic assignment of the
(interchangeable) zeros to the zero slots, every element gets an integer
displacement on the universal cover (shortest way round, adjusted so the sum is
zero). The window then sweeps and swaps an adjacent pair exactly when the pair
must cross on the cover. Two zeros never swap: they exchange displacements for
free, so zero blocks act as buffers. Sweeps run L-wise, R-wise, or greedy to
the nearest pair that must cross. The shortest word over all choices is freely
reduced (LR, RL, XX), replayed, and returned; control (a) is the fallback.
"""


def _replay(v, word):
    a = list(v)
    for ch in word:
        if ch == 'L':
            a.append(a.pop(0))
        elif ch == 'R':
            a.insert(0, a.pop())
        else:
            a[0], a[1] = a[1], a[0]
    return a


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL', 'XX'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _lifts(v, k, shift, m, r):
    n = len(v)
    zeros = [p for p in range(n) if v[p] == 0]
    target = [0] * n
    for p in range(n):
        if v[p]:
            target[p] = (k + v[p] - 1) % n
    for i in range(r):
        target[zeros[(shift + i) % r]] = (k + m + i) % n
    rem = [((target[p] - p + n // 2) % n) - n // 2 for p in range(n)]
    q = sum(rem) // n
    order = sorted(range(n), key=lambda p: rem[p], reverse=q > 0)
    for p in order[:abs(q)]:
        rem[p] -= n if q > 0 else -n
    return rem


def _sweep(v, rem, k, mode, limit=2000):
    n = len(v)
    a, rem = list(v), list(rem)
    out, c = [], 0

    def must_cross(x):
        return rem[x] - rem[(x + 1) % n] >= 2

    def cross(x):
        y = (x + 1) % n
        rx, ry = rem[x], rem[y]
        if a[x] == 0 and a[y] == 0:
            rem[x], rem[y] = ry + 1, rx - 1
            return
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
        if mode == 'L':
            out.append('L')
            c = (c + 1) % n
        else:
            out.append('R')
            c = (c - 1) % n
    if any(rem):
        return None
    d = (k - c) % n
    out.append('L' * d if d <= n - d else 'R' * (n - d))
    return ''.join(out)


def _naive(v):
    a = list(v)
    n, m = len(a), max(a)
    key = [x if x else m + 1 for x in a]
    out, c, end = [], 0, n - 1
    while end > 0:
        last = 0
        for i in range(end):
            if key[i] > key[i + 1]:
                k = (i - c) % n
                out.append(('L' * k if k <= n - k else 'R' * (n - k)) + 'X')
                c = i
                key[i], key[i + 1] = key[i + 1], key[i]
                last = i
        end = last
    k = (-c) % n
    out.append('L' * k if k <= n - k else 'R' * (n - k))
    return ''.join(out)


def sort_word(v):
    v = list(v)
    n, m = len(v), max(v)
    r = n - m
    goal = list(range(1, m + 1)) + [0] * r
    best = None
    for k in range(n):
        for shift in range(max(1, r)):
            rem = _lifts(v, k, shift, m, r) if r else None
            if rem is None:
                continue
            for mode in ('L', 'R', 'greedy'):
                w = _sweep(v, rem, k, mode)
                if w is not None:
                    w = _reduce(w)
                    if (best is None or len(w) < len(best)) and _replay(v, w) == goal:
                        best = w
    return best if best is not None else _naive(v)

```

## Evaluation Results

Performance data from evaluating the current component across test cases:

```
# Example 1
## instance
r5-s5

## r
5

## d_range
### Item 1
68

### Item 2
70

## within
37

## states
50

## invalid
0

## timeouts
0

## mean_excess
3.0

## seed_within
37

## seed_mean_excess
3.0

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r5-s5 (d 68..70), 50 states.
this candidate: within budget 37/50, worst r m9r5 at 0.740, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 3.000, max excess 6; instance score 0.8025; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r5 37/50 t0 e3.0
seed per (m,r) within/states, timeouts, mean excess: m9r5 37/50 t0 e3.0
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r5-104085652 v=(2, 3, 1, 0, 0, 0, 0, 9, 7, 8, 6, 0, 4, 5) r=5 T=73 d=69 OVER_BUDGET len=75
  word: LXLXLXRRXLXRRXLXLXRRRXLXLXLXLXLLLXLXLXLXRXRXRXLXLXRRRXLXLXLXLLLLXLXLXLXLXRR
  leaves every shortest path at step 5 (d 65 -> 66); T unreachable after step 32
  aligned optimal: LXLXRXRXRXLXLXLXLXLLLLXLXRRXLXLXLXRXRXRXRXLXLXLXLLLLXLXLXLXLXRXRXRXLX
- m9r5-100853423 v=(5, 1, 0, 4, 3, 0, 0, 0, 0, 9, 8, 7, 6, 2) r=5 T=73 d=70 OVER_BUDGET len=74
  word: XLXLXLXRXRRXRXLXRRXLXLXLXLXLXLLLLLXLXLXRXRXLXRRXLXLXRRRXLXLXRRRXLXLXLLLLLL
  leaves every shortest path at step 15 (d 56 -> 57); T unreachable after step 44
  aligned optimal: XLXLXLXRXRRXRXRRRRRXLXLXLXRRRXRXLXLXLXRRXRXRXLXLXLXRXRXRXRRXRXRXRXRXLX
- m9r5-108074006 v=(3, 2, 1, 0, 0, 9, 0, 8, 0, 6, 7, 5, 4, 0) r=5 T=73 d=70 OVER_BUDGET len=74
  word: LXLXLXLXLXLLXLXLXLXLXRXRXLXRRXLXRRRXRRRXRXRXLXLXLXLXRRRRRRXLXRRXRXRXRXRXRR
  leaves every shortest path at step 33 (d 38 -> 39); T unreachable after step 34
  aligned optimal: LXLXLXLXLXLLXLXLXLXLXRXRXLXRRXLXLLLLXLLXLXLXLXRRXRXRXRRXRXRXRXRXRRXRXL
- m9r5-216187103 v=(5, 3, 2, 0, 1, 0, 0, 6, 0, 0, 9, 8, 7, 4) r=5 T=73 d=70 OVER_BUDGET len=74
  word: XRXRXLXLXLLXLXLXLXLLXLXLLXLXLXLXLXLLLXLXLLXLXRRXLXLLLLXLXLXLXRRRRXLXLXRRRR
  leaves every shortest path at step 11 (d 60 -> 61); T unreachable after step 35
  aligned optimal: XRXRXLXLXLXRRRRXLXLXLXLXLLLLLXRXRXLXLXLXLXLXRXRXRXRXRRXLXRRXRXRRXRXRXR



# Example 2
## instance
r3-s6

## r
3

## d_range
### Item 1
56

### Item 2
59

## within
24

## states
50

## invalid
0

## timeouts
0

## mean_excess
1.96

## seed_within
24

## seed_mean_excess
1.96

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r3-s6 (d 56..59), 50 states.
this candidate: within budget 24/50, worst r m9r3 at 0.480, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 1.960, max excess 4; instance score 0.5645; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r3 24/50 t0 e1.96
seed per (m,r) within/states, timeouts, mean excess: m9r3 24/50 t0 e1.96
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r3-28554079 v=(5, 4, 3, 2, 1, 0, 0, 0, 7, 9, 8, 6) r=3 T=59 d=58 OVER_BUDGET len=62
  word: LXLXLXLXLXLXLLLXLXLXRXRXLXRRXLXLLLLXLXLXLXLXRRRXLXLXRRRXLXLXLX
  leaves every shortest path at step 11 (d 48 -> 49); T unreachable after step 11
  aligned optimal: LXLXLXLXLXRRXRXRXLXLXLXRXRXRRRRXRXLXLXRXRRXLXRXRRXRXRXRXLX
- m9r3-5443199 v=(1, 0, 0, 0, 9, 8, 7, 6, 5, 2, 4, 3) r=3 T=59 d=58 OVER_BUDGET len=62
  word: XLXLXLLXLXLXLXRXRXLXRRXLXLXLLLLXLXLXLXLXRRRRXLXLXLXRRRRXLXLXLX
  leaves every shortest path at step 7 (d 52 -> 53); T unreachable after step 7
  aligned optimal: XLXLXLXLXRRXLXRRXLXRRXLXRXRRRRXRXLXLXRXRRXLXLXLXLXRXRXRXRR
- m9r3-59202214 v=(0, 0, 9, 8, 7, 6, 5, 4, 1, 3, 2, 0) r=3 T=59 d=58 OVER_BUDGET len=62
  word: LXRXRXRXLXLXLXLLXLXLXLXRXRXLXRRXLXLXLLLLXLXLXLXLXRRRRRXLXLXLXL
  leaves every shortest path at step 16 (d 43 -> 44); T unreachable after step 16
  aligned optimal: LXRXRXRXLXLXLXLXRXRXRXRXRRRRXRXLXLXRXRXRXLXLXLXLXRXRXRXRRX
- m9r3-7257571 v=(2, 1, 0, 0, 8, 0, 7, 9, 6, 5, 4, 3) r=3 T=59 d=58 OVER_BUDGET len=62
  word: XLXLXRRXLXRRXLXLXLXLLLXLXLXLXRXRXLXRRXLXRRXLXLXLLLLXLXLXLXLXRR
  leaves every shortest path at step 6 (d 53 -> 54); T unreachable after step 6
  aligned optimal: XLXLXLXLXRRXRXRXRRRRXLXRXRXLXLXLXRXRXRXRXLXLXLXLLXLLXLXLXL



# Example 3
## instance
r2-s6

## r
2

## d_range
### Item 1
49

### Item 2
52

## within
39

## states
50

## invalid
0

## timeouts
0

## mean_excess
1.86

## seed_within
39

## seed_mean_excess
1.86

## feedback
SORT_PACKET_V2 (development only; search signal, not proof). Scope: instance r2-s6 (d 49..52), 50 states.
this candidate: within budget 39/50, worst r m9r2 at 0.780, sorted 50/50, timeouts (0.2 s CPU) 0, mean excess 1.860, max excess 4; instance score 0.8674; best so far (full development): combined 1.4075 (within 1356/1500, worst-r rate 0.830, mean excess 1.825)
this candidate per (m,r) within/states, timeouts, mean excess: m9r2 39/50 t0 e1.86
seed per (m,r) within/states, timeouts, mean excess: m9r2 39/50 t0 e1.86
Exact facts at m=9, r=1..5 (complete BFS tables): the sorting radius equals T_9(n) = 45, 52, 59, 66, 73. The 15 states at distance T are near-reversals: 10 of 15 read 9,8,...,1 cyclically, e.g. (2,1,0^r,9,8,...,3) for r=1,2,3 and (0^r,9,8,...,1) for r=2,3. d(v) <= min_q d_q(v) + K with K = 14,15,17,18,20 for r=1..5, where d_q is the (8,r) distance after deleting label q; K is attained only near the root. No rotation, reflection or complement symmetry preserves d.
- m9r2-1995836 v=(2, 1, 0, 0, 8, 9, 7, 6, 5, 4, 3) r=2 T=52 d=50 OVER_BUDGET len=54
  word: XLXLXRRXLXRRXLXLXLXLLLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRR
  leaves every shortest path at step 6 (d 45 -> 46); T unreachable after step 7
  aligned optimal: XLXLXLXRXRXRXRRRRXLXRXRXLXLXLXRXRXRXRRXRXRXRXLXLXL
- m9r2-19958387 v=(0, 0, 9, 7, 8, 6, 5, 4, 3, 2, 1) r=2 T=52 d=50 OVER_BUDGET len=54
  word: LXRXRXLXLXLLLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRRRRXLXLXLX
  leaves every shortest path at step 1 (d 50 -> 50); T unreachable after step 25
  aligned optimal: RXRRXLXRXRXRRRXRXRXLXLXLXRXRXRXRRXRXRXRXLXLXLXRXRX
- m9r2-3830396 v=(3, 2, 1, 0, 0, 8, 9, 7, 6, 5, 4) r=2 T=52 d=50 OVER_BUDGET len=54
  word: XLXRXRXLXLXLLLXLXLXLXRXRXLXRRXLXRRXLXLXLXLLLXLXLXLXRRR
  leaves every shortest path at step 4 (d 47 -> 47); T unreachable after step 13
  aligned optimal: XLXLXRXRXRRRRXRXLXLXLXRRXRXRXLXLXLXRXRXRXRRXRXRXLX
- m9r2-15920487 v=(9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0) r=2 T=52 d=50 OVER_BUDGET len=53
  word: LXLXLXLXRXRXLXRRXLXLXLLLXLXLXLXLXRXRXRXLXLXRRRXLXLXLX
  leaves every shortest path at step 5 (d 46 -> 46); T unreachable after step 15
  aligned optimal: LXLXRXRXLXLXLXRXRXRXRRRXRXRXRXLXLXLXLXRXRXRXLXLXRX
- m9r2-17758003 v=(0, 9, 8, 7, 6, 5, 4, 2, 3, 1, 0) r=2 T=52 d=50 OVER_BUDGET len=53
  word: XLXLXRXRXLXRRXLXLXLLLXLXLXLXLLXLXLXLXLXLLXLXLXRRXLXRR
  leaves every shortest path at step 12 (d 39 -> 39); T unreachable after step 30
  aligned optimal: XLXLXRXRXLXLLXRXRXRXRXLXLXLXLLLLXLXRRXLXLXLXRXRXRX


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
