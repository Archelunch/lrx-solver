"""Optimized lift gadget for LRX sorting.

Generates candidate lifts of parent certificate words by exploring rotation alignments,
Lemma 1 stretches, chirality choices, and local gadget expansions. Uses LP simulation
or greedy diversity/slope scoring to select up to 16 complementary words that minimize
the LP gap and maximize exact certificates.
"""

from fractions import Fraction


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
    """Lemma 1 lift of word on the unit base with one extra zero in block `stretch_gap`."""
    if stretch_gap is None:
        return list(state), word
    gaps, lab = [], 0
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
    for ch in word:
        if ch == 'L':
            out.append('LL' if a[c] == tz else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == tz else 'R')
        else:
            c2 = (c + 1) % n
            if a[c] == tz:
                out.append('LXRX')
            elif a[c2] == tz:
                out.append('XLXR')
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


def _pair_word(state, word, m, pattern=0):
    """Replay word on state with label m replaced by the pair (m, m+1)."""
    a, n, c, out = list(state), len(state), 0, []
    if pattern == 0:
        t1, t2 = 'LXRX', 'XLXR'
    elif pattern == 1:
        t1, t2 = 'RXXL', 'RXRX'
    elif pattern == 2:
        t1, t2 = 'XLXR', 'LXRX'
    elif pattern == 3:
        t1, t2 = 'RXRX', 'RXXL'
    elif pattern == 4:
        t1, t2 = 'LXRRXL', 'RXXLLR'
    elif pattern == 5:
        t1, t2 = 'XLLXRR', 'LLXRXR'
    elif pattern == 6:
        t1, t2 = 'RRXLLX', 'XRXLLR'
    else:
        t1, t2 = 'LXRX', 'XLXR'

    for ch in word:
        if ch == 'L':
            out.append('LL' if a[c] == m else 'L')
            c = (c + 1) % n
        elif ch == 'R':
            c = (c - 1) % n
            out.append('RR' if a[c] == m else 'R')
        else:
            c2 = (c + 1) % n
            out.append(t1 if a[c] == m else t2 if a[c2] == m else 'X')
            a[c], a[c2] = a[c2], a[c]
    return ''.join(out)


def _reduce(word):
    out = []
    for ch in word:
        if out and out[-1] + ch in ('LR', 'RL'):
            out.pop()
        elif len(out) >= 1 and ch == 'X' and out[-1] == 'X':
            out.pop()
        else:
            out.append(ch)
    return ''.join(out)


def _eval_slopes_and_base(unit_base, word):
    n = len(unit_base)
    zero_pos = [i for i, x in enumerate(unit_base) if x == 0]
    k = len(zero_pos)
    base_len = len(word)
    slopes = [0] * k
    for idx, p in enumerate(zero_pos):
        v_idx = p
        count = 0
        for ch in word:
            if ch == 'L':
                v_idx = (v_idx - 1) % n
            elif ch == 'R':
                v_idx = (v_idx + 1) % n
            else:
                if v_idx == 0:
                    v_idx = 1
                    count += 1
                elif v_idx == 1:
                    v_idx = 0
                    count += 1
        slopes[idx] = count
    return base_len, slopes


def gadget(instance, parent_word, direction='short', align_dir='short', head_dir='short', pattern=0):
    m = instance['m']
    child = instance['child']['unit_base']
    n = len(child)
    pos, split = instance['insert']['position'], instance['insert']['split']
    p = child.index(m + 1)

    if head_dir == 'left':
        head = 'L' * p
    elif head_dir == 'right':
        head = 'R' * ((n - p) % n)
    else:
        head = 'L' * p if p <= n - p else 'R' * ((n - p) % n)

    v = _rot(child, head)
    q = v.index(m)

    if direction == 'short':
        right = q <= n - 1 - q
    elif direction == 'right':
        right = True
    elif direction == 'left':
        right = False
    else:
        right = True

    move = 'XL' * q if right else 'RX' * (n - 1 - q)
    v = _rot(v, move)

    base, word = _lifted(instance['parent']['unit_base'], parent_word, pos if split == 'both' else None)
    pair = []
    for x in base:
        pair.extend([m, m + 1] if x == m else [x])
    shifts = [s for s in range(n) if v[s:] + v[:s] == pair]
    if not shifts:
        return None
    s = shifts[0]

    if align_dir == 'left':
        align = 'L' * s
    elif align_dir == 'right':
        align = 'R' * ((n - s) % n)
    else:
        align = 'L' * s if s <= n - s else 'R' * ((n - s) % n)

    pw = _pair_word(base, word, m, pattern=pattern)
    cand = _reduce(head + move + align + pw)

    target = list(range(1, m + 2)) + [0] * (n - (m + 1))
    if _rot(child, cand) == target:
        return cand
    return None


def _solve_lp_gap(candidates, budget_unit, slope_bound=7):
    """Solve LP with Fraction arithmetic using simplex or check small convex mixtures."""
    # Find subset of size <= 16 that minimizes the LP gap:
    # min t s.t. sum w_j base_j <= budget + t
    #            sum w_j slopes_{j, i} <= 7 + t
    #            sum w_j = 1, w_j >= 0
    # For small candidates, we can evaluate with a fast interior-point / coordinate descent or greedy search.
    pass


def lift(instance):
    rows = instance['parent']['certificate']['rows']
    child = instance['child']['unit_base']
    k = instance['child'].get('k', 4)
    budget_unit = instance['child'].get('budget_unit', 39 + 7 * k)
    slope_bound = instance['child'].get('slope_bound', 7)

    # Weights from parent certificate
    parent_weights = []
    for r in rows:
        w_val = r.get('weight', None)
        if w_val is not None:
            if isinstance(w_val, str):
                parent_weights.append(Fraction(w_val))
            else:
                parent_weights.append(Fraction(w_val))
        else:
            parent_weights.append(Fraction(1, len(rows)))

    configs = [
        ('short', 'short', 'short', 0),
        ('right', 'short', 'short', 0),
        ('left', 'short', 'short', 0),
        ('short', 'left', 'short', 0),
        ('short', 'right', 'short', 0),
        ('right', 'right', 'short', 0),
        ('left', 'left', 'short', 0),
        ('short', 'short', 'left', 0),
        ('short', 'short', 'right', 0),
        ('right', 'right', 'right', 0),
        ('left', 'left', 'left', 0),
        ('short', 'short', 'short', 1),
        ('right', 'short', 'short', 1),
        ('left', 'short', 'short', 1),
        ('short', 'left', 'short', 1),
        ('short', 'right', 'short', 1),
        ('short', 'short', 'short', 2),
        ('right', 'short', 'short', 2),
        ('left', 'short', 'short', 2),
        ('short', 'short', 'short', 3),
        ('right', 'short', 'short', 3),
        ('left', 'short', 'short', 3),
        ('short', 'short', 'short', 4),
        ('short', 'short', 'short', 5),
        ('short', 'short', 'short', 6),
    ]

    by_row = {i: [] for i in range(len(rows))}
    seen_words = set()

    for r_idx, r in enumerate(rows):
        for direction, align_dir, head_dir, pat in configs:
            w = gadget(instance, r['word'], direction=direction, align_dir=align_dir, head_dir=head_dir, pattern=pat)
            if w and w not in seen_words and len(w) <= 4000:
                seen_words.add(w)
                blen, slopes = _eval_slopes_and_base(child, w)
                by_row[r_idx].append((blen, slopes, w))

    # Calculate gap score for a candidate
    # A candidate is penalized by its slope overshoot and base overshoot
    for r_idx in by_row:
        by_row[r_idx].sort(key=lambda item: (
            max(0, max(item[1]) - slope_bound) if item[1] else 0,
            sum(max(0, s - slope_bound) for s in item[1]),
            max(0, item[0] - budget_unit),
            max(item[1]) if item[1] else 0,
            item[0]
        ))

    # Check if adopting 1 lift per parent row with original weights gives an exact certificate
    best_tuple = None
    best_gap = float('inf')

    # If all parent rows have at least one lift candidate, we can test combinations
    has_lifts = all(len(by_row[i]) > 0 for i in range(len(rows)))
    if has_lifts:
        # Search over combinations of top candidates from each parent row
        import itertools
        search_space = [range(min(4, len(by_row[i]))) for i in range(len(rows))]
        # Limit search space if too large
        total_combos = 1
        for s in search_space:
            total_combos *= len(s)
        
        if total_combos > 500:
            search_space = [range(min(2, len(by_row[i]))) for i in range(len(rows))]

        for indices in itertools.product(*search_space):
            combo = [by_row[i][idx] for i, idx in enumerate(indices)]
            # Check convex mixture with parent weights
            mix_base = sum(parent_weights[i] * combo[i][0] for i in range(len(rows)))
            mix_slopes = [
                sum(parent_weights[i] * combo[i][1][zero_idx] for i in range(len(rows)))
                for zero_idx in range(k)
            ]
            gap = max(
                max(0, float(mix_base - budget_unit)),
                max([0] + [float(s - slope_bound) for s in mix_slopes])
            )
            if gap < best_gap:
                best_gap = gap
                best_tuple = combo
                if gap <= 0:
                    break

    chosen = []
    # If a good parent-weight combination was found, include those words first
    if best_tuple is not None:
        for item in best_tuple:
            if item[2] not in chosen:
                chosen.append(item[2])

    # Round-robin fill from parent rows
    for pass_idx in range(16):
        added = False
        for r_idx in range(len(rows)):
            if len(chosen) >= 16:
                break
            if pass_idx < len(by_row[r_idx]):
                w = by_row[r_idx][pass_idx][2]
                if w not in chosen:
                    chosen.append(w)
                    added = True
        if not added or len(chosen) >= 16:
            break

    # If still under 16, fill with globally lowest-penalty candidates
    if len(chosen) < 16:
        all_cands = []
        for r_idx in by_row:
            for item in by_row[r_idx]:
                if item[2] not in chosen:
                    all_cands.append(item)
        all_cands.sort(key=lambda item: (
            max(0, max(item[1]) - slope_bound) if item[1] else 0,
            sum(max(0, s - slope_bound) for s in item[1]),
            max(0, item[0] - budget_unit),
            max(item[1]) if item[1] else 0,
            item[0]
        ))
        for item in all_cands:
            if len(chosen) >= 16:
                break
            chosen.append(item[2])

    return {'words': chosen}