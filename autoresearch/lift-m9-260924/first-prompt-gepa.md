# First GEPA proposer prompt (lift-m9-260924)

This is the exact `messages` array the GEPA reflection client sends to the local broker on iteration 1 for the seed program. The broker forwards it unchanged, adding only transport fields (see `broker-config.json` and the `--dry-run` payload). It was captured offline from a zero-provider GEPA run with the frozen development set. Only development data appears; the holdout set is never loaded.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `6afea585ee3f8cdf9edd66e26f8d2690a4fe2232d5cf809a0b6fa1d1e3b5c48b`
- Message roles: ['user']. GEPA sends no separate system message; the system text is embedded in the user message as GEPA's background.
- Client request fields: model `grok-4.7`, max_tokens `4096`, reasoning_effort `low`
- Captured from: `smoke-gepa-first-prompt` (request-0001.json)
- A live GEPA run halts before its first model request if these messages hash differently.

## Message 1: user

``````text
You are an expert optimization assistant. Your task is to analyze evaluation feedback and propose an improved version of a system component.

## Optimization Goal

Improve this executable Python lift(instance) gadget. Return the entire replacement Python source in one fenced code block. Maximize exact m=9 family certificates, then reduce the exact LP gap on misses. Only development instances are shown.

## Domain Context & Constraints

Find a label-insertion gadget for LRX sorting. The candidate source must define lift(instance) and return {'words': [...], 'weights': optional rational strings, 'note': optional}: at most 16 strings over L,R,X, each at most 4000 letters, and each sorting the child unit base to (1..9, 0^k). L rotates the vector left, R rotates it right, and X swaps its first two entries. The source must be at most 64 KiB, use the standard library only, and finish each instance within 10 seconds. The instance is {m: 8, parent: {id, labels, mask, unit_base, certificate: {kind, rows: [{weight, word, base, slopes}]}}, insert: {label: 9, position, split}, child: {id, labels, mask, unit_base, k, budget_unit, slope_bound}}. Parent rows are certified m=8 words on the parent unit base, with exact Lemma 1 base and one slope per zero block. The trusted evaluator replays every word, recomputes base and slopes, and solves the exact LP. A certificate needs weighted base < budget_unit+1 = 39+7k and every weighted slope <= 7. A uniform gadget adds at most n letters and raises each slope by at most 1. Misses prove nothing. Do not read files, the network, or environment variables.

## Current Component

The component being optimized:

```
"""Naive control gadget for the lift task (stdlib, self-contained, deterministic).

For each parent row word W: rotate label m+1 to the front, bubble it cyclically
until it sits right after label m, rotate the remaining atoms onto the parent
unit base (a 'both' split leaves two adjacent zeros, i.e. W lifted by Lemma 1
with z=1 on that block), then replay W treating the pair (m, m+1) as one atom:
L/R over the pair doubles, X with the pair uses a 4-letter transposition.
It is a control, not a target.
"""


def _rot(v, word):
    v = list(v)
    for ch in word:
        if ch == 'L':
            v = v[1:] + v[:1]
        elif ch == 'R':
            v = v[-1:] + v[:-1]
        else:
            v[0], v[1] = v[1], v[0]
    return v


def _lifted(state, word, stretch_gap):
    """Lemma 1 lift of word on the unit base with one extra zero in block `stretch_gap`
    (None = no stretch).  Returns (stretched state, word)."""
    if stretch_gap is None:
        return list(state), word
    gaps, lab = [], 0  # gap of each zero
    for x in state:
        if x:
            lab += 1
        else:
            gaps.append(lab)
    target = gaps.index(stretch_gap)
    a, zi = [], 0
    for x in state:
        if x:
            a.append(x)
        else:
            a.append(-(zi + 1))
            zi += 1
    tz = -(target + 1)
    out = []
    n = len(a)
    c = 0
    for ch in word:  # physical cursor model; the stretched block is 2 zeros wide
        if ch == 'L':
            out.append('LL' if a[c] == tz else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == tz else 'R')
        else:
            c2 = (c + 1) % n
            if a[c] == tz:
                out.append('LXRX')      # (0^2, y) -> (y, 0^2)
            elif a[c2] == tz:
                out.append('XLXR')      # (y, 0^2) -> (0^2, y)
            else:
                out.append('X')
            a[c], a[c2] = a[c2], a[c]
    st, zi = [], 0
    for x in state:
        if x:
            st.append(x)
        else:
            st.extend([0, 0] if zi == target else [0])
            zi += 1
    return st, ''.join(out)


def _pair_word(state, word, m):
    """Replay word on state with label m replaced by the pair (m, m+1)."""
    a, n, c, out = list(state), len(state), 0, []
    for ch in word:
        if ch == 'L':
            out.append('LL' if a[c] == m else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == m else 'R')
        else:
            c2 = (c + 1) % n
            out.append('LXRX' if a[c] == m else 'XLXR' if a[c2] == m else 'X')
            a[c], a[c2] = a[c2], a[c]
    return ''.join(out)


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL'):
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


# Bubble direction for label m+1: 'short' (fewer letters), 'right', 'left'.
DIRECTIONS = ('short',)


def gadget(instance, parent_word, direction='short'):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)
    head = 'L' * p if p <= n - p else 'R' * (n - p)
    v = _rot(child, head)
    q = v.index(m)
    right = q <= n - 1 - q if direction == 'short' else direction == 'right'
    move = 'XL' * q if right else 'RX' * (n - 1 - q)
    v = _rot(v, move)
    base, word = _lifted(instance['parent']['unit_base'], parent_word, pos if split == 'both' else None)
    pair = []
    for x in base:
        pair.extend([m, m + 1] if x == m else [x])
    shifts = [s for s in range(n) if v[s:] + v[:s] == pair]
    s = shifts[0]
    align = 'L' * s if s <= n - s else 'R' * (n - s)
    return _reduce(head + move + align + _pair_word(base, word, m))


def lift(instance):
    rows = instance['parent']['certificate']['rows']
    words = []
    for direction in DIRECTIONS:
        for r in rows:
            w = gadget(instance, r['word'], direction)
            if w not in words and len(words) < 16:
                words.append(w)
    return {'words': words,
            'note': 'naive control: bubble m+1 next to m, replay parent words with a paired atom'}

```

## Evaluation Results

Performance data from evaluating the current component across test cases:

```
# Example 1
## parent_id
k5-mask218-order33927

## certificates
1

## valid
19

## instances
19

## gap_sum
63.49447150440413

## feedback
LIFT_PACKET_V1 (parent k5-mask218-order33927; development only; search signal, not proof)
this candidate: 1/19 certificates, 19/19 valid, gap_sum 63.494; best so far: screen 56.6166 (56/306 certificates); full development 285/4588 certificates
- lift-k5-mask218-order33927-i7-both child [7, 0, 6, 1, 0, 5, 0, 4, 3, 0, 8, 0, 9, 0, 2] k=6 need base<81, slopes<=7: gap 0.714, mixture base 81.00, overshoot 0, slopes over 7 [[1, '51/7'], [2, '54/7'], [3, '54/7'], [4, '54/7']]; parent rows used [1]; parent rows [{"base":52,"row":0,"slopes":[4,8,11,6,3],"w":"2/5"},{"base":56,"row":1,"slopes":[5,11,9,3,0],"w":"3/25"},{"base":65,"row":2,"slopes":[9,3,0,6,9],"w":"2/5"},{"base":56,"row":3,"slopes":[0,6,9,8,5],"w":"3/100"}]
- lift-k5-mask218-order33927-i0-none child [9, 7, 0, 6, 1, 0, 5, 0, 4, 3, 0, 8, 0, 2] k=5 need base<74, slopes<=7: gap 0.750, mixture base 74.00, overshoot 0, slopes over 7 [[1, '29/4'], [2, '31/4'], [3, '31/4'], [4, '31/4']]; parent rows used [0, 1, 2, 3, 4]; parent rows [{"base":52,"row":0,"slopes":[4,8,11,6,3],"w":"2/5"},{"base":56,"row":1,"slopes":[5,11,9,3,0],"w":"3/25"},{"base":65,"row":2,"slopes":[9,3,0,6,9],"w":"2/5"},{"base":56,"row":3,"slopes":[0,6,9,8,5],"w":"3/100"}]
- lift-k5-mask218-order33927-i7-left child [7, 0, 6, 1, 0, 5, 0, 4, 3, 0, 8, 0, 9, 2] k=5 need base<74, slopes<=7: gap 0.750, mixture base 74.00, overshoot 0, slopes over 7 [[1, '29/4'], [2, '31/4'], [3, '31/4'], [4, '31/4']]; parent rows used [0, 1, 2, 3, 4]; parent rows [{"base":52,"row":0,"slopes":[4,8,11,6,3],"w":"2/5"},{"base":56,"row":1,"slopes":[5,11,9,3,0],"w":"3/25"},{"base":65,"row":2,"slopes":[9,3,0,6,9],"w":"2/5"},{"base":56,"row":3,"slopes":[0,6,9,8,5],"w":"3/100"}]
failed construction (lift-k5-mask218-order33927-i7-both, word 1, LP weight 15/28): base 71, slopes [5, 11, 12, 6, 3, 2], word RRRRXLLLLXRXLLXLXLXLXLLXRXRRRXRXRXLLXLXLXLLLXLLXLXRRXLXRRRXRXRRXLXRXRRX



# Example 2
## parent_id
k9-mask511-order33979

## certificates
1

## valid
27

## instances
27

## gap_sum
261.18497536945813

## feedback
LIFT_PACKET_V1 (parent k9-mask511-order33979; development only; search signal, not proof)
this candidate: 1/27 certificates, 27/27 valid, gap_sum 261.185; best so far: screen 56.6166 (56/306 certificates); full development 285/4588 certificates
- lift-k9-mask511-order33979-i5-both child [0, 7, 0, 6, 0, 2, 0, 1, 0, 8, 0, 9, 0, 3, 0, 5, 0, 4, 0] k=10 need base<109, slopes<=7: gap 4.500, mixture base 111.50, overshoot 5/2, slopes over 7 [[0, '15/2'], [1, '9'], [2, '9'], [3, '15/2'], [8, '17/2'], [9, '17/2']]; parent rows used [2]; parent rows [{"base":71,"row":0,"slopes":[6,3,0,3,6,9,11,8,5],"w":"5/11"},{"base":84,"row":1,"slopes":[4,5,8,12,9,6,3,0,3],"w":"4/33"},{"base":85,"row":2,"slopes":[8,11,9,6,3,0,3,6,9],"w":"7/33"},{"base":91,"row":3,"slopes":[5,8,11,9,6,3,0,3,6],"w":"7/33"}]
- lift-k9-mask511-order33979-i5-left child [0, 7, 0, 6, 0, 2, 0, 1, 0, 8, 0, 9, 3, 0, 5, 0, 4, 0] k=9 need base<102, slopes<=7: gap 5.444, mixture base 106.61, overshoot 83/18, slopes over 7 [[1, '15/2'], [2, '67/9'], [3, '47/6'], [5, '47/6'], [6, '23/3'], [7, '47/6'], [8, '70/9']]; parent rows used [0, 1, 2, 3]; parent rows [{"base":71,"row":0,"slopes":[6,3,0,3,6,9,11,8,5],"w":"5/11"},{"base":84,"row":1,"slopes":[4,5,8,12,9,6,3,0,3],"w":"4/33"},{"base":85,"row":2,"slopes":[8,11,9,6,3,0,3,6,9],"w":"7/33"},{"base":91,"row":3,"slopes":[5,8,11,9,6,3,0,3,6],"w":"7/33"}]
failed construction (lift-k9-mask511-order33979-i5-both, word 2, LP weight 3/4): base 109, slopes [8, 11, 12, 9, 6, 3, 2, 5, 8, 9], word RRRRRRRRRXLLLLLLLXLXLLXRXRRRRXLXLXLXLXLLXLLXLLXRXLLLXLXRRXLXRRXLXRRRXRXRXRXRXRRRRRRXLXLXLXLXLXLLLLLXRXRXRXRXR



# Example 3
## parent_id
k6-mask470-order7602

## certificates
1

## valid
21

## instances
21

## gap_sum
108.22916666666667

## feedback
LIFT_PACKET_V1 (parent k6-mask470-order7602; development only; search signal, not proof)
this candidate: 1/21 certificates, 21/21 valid, gap_sum 108.229; best so far: screen 56.6166 (56/306 certificates); full development 285/4588 certificates
- lift-k6-mask470-order7602-i6-right child [2, 0, 5, 0, 6, 3, 0, 8, 1, 9, 0, 4, 0, 7, 0] k=6 need base<81, slopes<=7: gap 1.750, mixture base 81.00, overshoot 0, slopes over 7 [[1, '35/4'], [2, '35/4']]; parent rows used [0, 1, 2, 3, 4]; parent rows [{"base":69,"row":0,"slopes":[6,3,3,9,11,8],"w":"1/5"},{"base":72,"row":1,"slopes":[0,3,9,8,5,2],"w":"1/20"},{"base":56,"row":2,"slopes":[10,10,4,2,5,8],"w":"2/5"},{"base":73,"row":3,"slopes":[3,0,6,12,8,5],"w":"1/10"}]
- lift-k6-mask470-order7602-i6-both child [2, 0, 5, 0, 6, 3, 0, 8, 1, 0, 9, 0, 4, 0, 7, 0] k=7 need base<88, slopes<=7: gap 1.812, mixture base 88.00, overshoot 0, slopes over 7 [[1, '141/16'], [2, '141/16'], [3, '29/4']]; parent rows used []; parent rows [{"base":69,"row":0,"slopes":[6,3,3,9,11,8],"w":"1/5"},{"base":72,"row":1,"slopes":[0,3,9,8,5,2],"w":"1/20"},{"base":56,"row":2,"slopes":[10,10,4,2,5,8],"w":"2/5"},{"base":73,"row":3,"slopes":[3,0,6,12,8,5],"w":"1/10"}]
- lift-k6-mask470-order7602-i6-left child [2, 0, 5, 0, 6, 3, 0, 8, 1, 0, 9, 4, 0, 7, 0] k=6 need base<81, slopes<=7: gap 2.000, mixture base 81.00, overshoot 0, slopes over 7 [[1, '9'], [2, '9']]; parent rows used [0, 1, 2, 3, 4]; parent rows [{"base":69,"row":0,"slopes":[6,3,3,9,11,8],"w":"1/5"},{"base":72,"row":1,"slopes":[0,3,9,8,5,2],"w":"1/20"},{"base":56,"row":2,"slopes":[10,10,4,2,5,8],"w":"2/5"},{"base":73,"row":3,"slopes":[3,0,6,12,8,5],"w":"1/10"}]
failed construction (lift-k6-mask470-order7602-i6-right, word 2, LP weight 23/48): base 76, slopes [10, 13, 7, 4, 7, 10], word RRRRRRRXLLLLLLLXRRXLXLXLXLLXLXRXRXRXRRRRRXLXLXLXLXLLLXLLLXLXRRXLXLLLXLXLXLXL


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
