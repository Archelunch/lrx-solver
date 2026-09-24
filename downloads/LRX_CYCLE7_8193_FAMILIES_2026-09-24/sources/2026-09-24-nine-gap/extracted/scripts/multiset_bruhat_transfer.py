"""Transfer a reverse-circle sorting word through an unused physical cut.

Only the zero pattern and label order are fixed in the input. The mask
conditions are independent of subsequent positive zero-block expansions.
This module does not assume that reverse label orders are globally worst.
"""
from itertools import permutations
from fractions import Fraction

from multiset_free_phase import stable_ranks, replay
from multiset_zero_stretch import expanded_state, certificate
from multiset_box_certificate import lifted_row


def word_geometry(n, word):
    at, used = 0, set()
    for letter in word:
        if letter == 'X':
            used.add(at)
        else:
            assert letter in 'LR'
            at = (at + (1 if letter == 'L' else -1)) % n
    return at, tuple(cut for cut in range(n) if (cut-1) % n not in used)


def row_clauses(base, row):
    """Each clause is (first named-position index, interval size, label mask).

    The returned physical cut belongs to the refined base row['origin'].
    It is a boundary between its atomic positions, never inside an atom.
    """
    reference = expanded_state(base, row['origin'])
    n, m = len(reference), max(reference)
    labels = tuple(x for x in reference if x)
    assert all(labels[(i+1) % m] == 1+(labels[i]-2) % m for i in range(m))
    finish, cuts = word_geometry(n, row['word'])
    result = {}
    for cut in cuts:
        start = sum(x != 0 for x in reference[:cut]) % m
        window = labels[start:] + labels[:start]
        order = sorted(range(1, m+1), key=lambda x: (x-1+finish-cut) % n)
        ranks = {x: i for i, x in enumerate(order)}
        q = tuple(ranks[x] for x in window)
        size = q[0]+1
        expected = tuple(range(size-1, -1, -1)) + tuple(range(m-1, size-1, -1))
        assert q == expected
        mask = sum(1 << (x-1) for x in window[:size])
        result.setdefault((start, size, mask), cut)
    return result


def satisfies(labels, clause):
    start, size, expected = clause
    m = len(labels)
    return sum(1 << (labels[(start+j) % m]-1) for j in range(size)) == expected


def transfer_cut(base, row, labels):
    assert sorted(labels) == list(range(1, max(base)+1))
    for clause, cut in row_clauses(base, row).items():
        if satisfies(labels, clause):
            return cut
    return None


def comparator_word(state, word, cut):
    """Use the same paid cursor motion and compare at every reference X."""
    state = tuple(state)
    n, m = len(state), max(state)
    finish, cuts = word_geometry(n, word)
    assert cut in cuts
    p = list(stable_ranks(state, cut, (finish-cut) % n))
    at, output = (-cut) % n, []
    for letter in word:
        if letter == 'X':
            assert at < n-1
            if p[at] > p[at+1]:
                p[at], p[at+1] = p[at+1], p[at]
                output.append('X')
        else:
            at = (at + (1 if letter == 'L' else -1)) % n
            output.append(letter)
    assert p == list(range(n))
    answer = ''.join(output)
    assert len(answer) <= len(word)
    assert replay(state, answer) == tuple(range(1, m+1)) + (0,)*(n-m)
    return answer


def relabel_base(base, labels):
    iterator = iter(labels)
    result = tuple(next(iterator) if value else 0 for value in base)
    assert next(iterator, None) is None
    return result


def inversions(rank):
    return sum(a > b for i, a in enumerate(rank) for b in rank[i+1:])


def zero_inversions(rank, zero_at, named_positions):
    z = rank[zero_at]
    return sum((j < zero_at and rank[j] > z) or (j > zero_at and rank[j] < z)
               for j in named_positions)


def comparison_profile(base, row, labels, cut=None):
    """Exact price of the unshortened comparison lift, for all lengths >= origin."""
    labels = tuple(labels)
    if cut is None:
        cut = transfer_cut(base, row, labels)
    if cut is None:
        return None
    assert any(value == cut and satisfies(labels, clause)
               for clause, value in row_clauses(base, row).items())
    reference = expanded_state(base, row['origin'])
    actual = relabel_base(reference, labels)
    n = len(reference)
    finish, _ = word_geometry(n, row['word'])
    end = (finish-cut) % n
    q, p = stable_ranks(reference, cut, end), stable_ranks(actual, cut, end)
    window = reference[cut:] + reference[:cut]
    named = [i for i, x in enumerate(window) if x]
    assert all(p[i] == q[i] for i, x in enumerate(window) if x == 0)
    # Direct prefix comparison, independent of the reverse-order mask criterion.
    for length in range(1, n+1):
        for threshold in range(n):
            assert sum(x <= threshold for x in p[:length]) >= sum(x <= threshold for x in q[:length])
    cert = certificate(reference, row['word'])
    assert cert['x_count'] == inversions(q)
    positions = [i for i, x in enumerate(reference) if x == 0]
    beta, gains = [], []
    for old_beta, pick in zip(row['beta'], row['picks']):
        zero_at = (positions[pick]-cut) % n
        before, after = zero_inversions(q, zero_at, named), zero_inversions(p, zero_at, named)
        assert before == cert['zero_swaps'][pick] and before >= after
        gains.append(before-after)
        beta.append(old_beta-before+after)
    gain = inversions(q)-inversions(p)
    assert gain >= 0
    return dict(reference_base=tuple(base), target_base=relabel_base(base, labels),
                reference_row=row, cut=cut, origin=row['origin'],
                base_cost=row['base_cost']-gain, beta=beta,
                saved_base_swaps=gain, saved_zero_slopes=gains)


def comparison_price(profile, lengths):
    assert len(lengths) == len(profile['origin'])
    assert all(type(x) is int and x >= origin for x, origin in zip(lengths, profile['origin']))
    return profile['base_cost'] + sum(b*(length-origin)
        for b, length, origin in zip(profile['beta'], lengths, profile['origin']))


def comparison_lift(profile, lengths, *, max_positions=100000, max_letters=500000):
    """Materialize the comparison word with the reference's paid rotations."""
    base, row = profile['reference_base'], profile['reference_row']
    predicted = comparison_price(profile, lengths)
    if max(base)+sum(lengths) > max_positions or predicted > max_letters:
        raise RuntimeError('Explicit comparison-lift cap exceeded; use symbolic price')
    reference = expanded_state(base, row['origin'])
    atom_lengths = [1]*sum(row['origin'])
    for length, origin, pick in zip(lengths, row['origin'], row['picks']):
        assert length >= origin
        atom_lengths[pick] += length-origin
    cursor_cut, ordinal = 0, 0
    for i, value in enumerate(reference):
        weight = 1 if value else atom_lengths[ordinal]
        if i < profile['cut']:
            cursor_cut += weight
        ordinal += value == 0
    word = lifted_row(base, row, lengths)
    actual = expanded_state(profile['target_base'], lengths)
    result = comparator_word(actual, word, cursor_cut)
    assert len(result) == predicted
    return result


def transferred_atomic_word(base, row, labels, cut=None):
    """A new finite sorting word; its own stretch profile must be recomputed."""
    from multiset_phase_service import shorten_circle_runs
    from multiset_weighted_interleaving import free_reduce
    cut = transfer_cut(base, row, labels) if cut is None else cut
    if cut is None:
        return None
    actual = relabel_base(expanded_state(base, row['origin']), labels)
    word = comparator_word(actual, row['word'], cut)
    while True:
        shorter = free_reduce(shorten_circle_runs(word, len(actual)))
        if shorter == word:
            return word
        assert len(shorter) <= len(word)
        word = shorter


def clause_bitsets(m=8):
    """All label permutations, indexed lexicographically, using byte bitsets."""
    orders = tuple(permutations(range(1, m+1)))
    size, arrays = (len(orders)+7)//8, {}
    for index, labels in enumerate(orders):
        byte, bit = divmod(index, 8)
        for start in range(m):
            mask = 0
            for width in range(1, m+1):
                mask |= 1 << (labels[(start+width-1) % m]-1)
                key = start, width, mask
                if key not in arrays:
                    arrays[key] = bytearray(size)
                arrays[key][byte] |= 1 << bit
    return orders, {key: int.from_bytes(value, 'little') for key, value in arrays.items()}


def tree_domain(base, tree, bits, all_orders):
    if tree['kind'] == 'split':
        return tree_domain(base, tree['left'], bits, all_orders) & tree_domain(base, tree['right'], bits, all_orders)
    assert tree['kind'] == 'affine'
    answer = all_orders
    for row in tree['rows']:
        if Fraction(row['weight']) == 0:
            continue
        domain = 0
        for clause in row_clauses(base, row):
            domain |= bits[clause]
        answer &= domain
    return answer


def tree_accepts(base, tree, labels):
    if tree['kind'] == 'split':
        return tree_accepts(base, tree['left'], labels) and tree_accepts(base, tree['right'], labels)
    assert tree['kind'] == 'affine'
    return all(Fraction(row['weight']) == 0 or transfer_cut(base, row, labels) is not None
               for row in tree['rows'])


def transferred_tree_word(reference_base, tree, labels, lengths):
    """Construct a certified word on an accepted order in the same zero pattern."""
    assert tree_accepts(reference_base, tree, labels)
    node = tree
    while node['kind'] == 'split':
        node = node['left'] if lengths[node['axis']] <= node['cut'] else node['right']
    candidates = [comparison_profile(reference_base, row, labels)
                  for row in node['rows'] if Fraction(row['weight']) > 0]
    profile = min(candidates, key=lambda p: comparison_price(p, lengths))
    word = comparison_lift(profile, lengths)
    m, n = max(reference_base), max(reference_base)+sum(lengths)
    assert len(word) <= (m-2)*n-(m*m-3*m-4)//2
    return word
