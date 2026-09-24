"""Parametric lifting of an LRX word by replacing zeros with zero blocks.

After cancelling adjacent opposite rotations, the length is an explicit
affine function of the added block lengths. No cover
bound is assumed. No exchange of two zero atoms is allowed in the input.
"""

from multiset_free_phase import replay


def tagged(state):
    result = []
    zeros = 0
    for value in state:
        assert value >= 0
        if value:
            result.append(value)
        else:
            zeros += 1
            result.append(-zeros)
    return result, zeros


def cancel_rotations(word):
    result = []
    for letter in word:
        if result and (result[-1], letter) in (('L', 'R'), ('R', 'L')):
            result.pop()
        else:
            result.append(letter)
    return ''.join(result)


def remove_zero_swaps(state, word):
    a = list(state)
    kept = []
    for letter in word:
        if letter == 'L':
            a = a[1:]+a[:1]
        elif letter == 'R':
            a = a[-1:]+a[:-1]
        else:
            assert letter == 'X'
            if a[0] == a[1] == 0:
                continue
            a[0], a[1] = a[1], a[0]
        kept.append(letter)
    return ''.join(kept)


def certificate(state, word):
    """Return swap multiplicities and affine boundary-rotation gaps.

    A gap is (constant, coefficient vector) in z_j = block_length_j-1.
    beta_j = 2*zero_swaps_j + sum_gaps abs(coefficient_j).
    """
    atoms, r = tagged(state)
    swaps = [0]*r
    gaps = []
    constant = 0
    coeff = [0]*r
    x_count = 0
    for letter in word:
        if letter == 'L':
            constant += 1
            if atoms[0] < 0:
                coeff[-atoms[0]-1] += 1
            atoms = atoms[1:]+atoms[:1]
        elif letter == 'R':
            constant -= 1
            if atoms[-1] < 0:
                coeff[-atoms[-1]-1] -= 1
            atoms = atoms[-1:]+atoms[:-1]
        else:
            assert letter == 'X' and not (atoms[0] < 0 and atoms[1] < 0)
            x_count += 1
            if atoms[0] < 0:
                j = -atoms[0]-1
                swaps[j] += 1
                coeff[j] += 1  # L^(length-1) before the first expanded X.
            elif atoms[1] < 0:
                swaps[-atoms[1]-1] += 1
            gaps.append((constant, tuple(coeff)))
            constant, coeff = 0, [0]*r
            if atoms[1] < 0:
                coeff[-atoms[1]-1] -= 1  # R^(length-1) after the last expanded X.
            atoms[0], atoms[1] = atoms[1], atoms[0]
    gaps.append((constant, tuple(coeff)))
    for c, row in gaps:
        assert (c >= 0 and all(v >= 0 for v in row)) or (c <= 0 and all(v <= 0 for v in row))
    beta = tuple(2*swaps[j]+sum(abs(row[j]) for _, row in gaps) for j in range(r))
    base_cost = x_count+sum(abs(c) for c, _ in gaps)
    assert base_cost == len(cancel_rotations(word))
    return dict(zeros=r, x_count=x_count, zero_swaps=tuple(swaps), gaps=tuple(gaps),
                base_cost=base_cost, beta=beta,
                final=tuple(v if v > 0 else 0 for v in atoms))


def exact_length(cert, lengths):
    assert len(lengths) == cert['zeros'] and min(lengths, default=1) >= 1
    extra = [length-1 for length in lengths]
    return (cert['x_count']+2*sum(a*z for a, z in zip(cert['zero_swaps'], extra))
            +sum(abs(c+sum(v*z for v, z in zip(row, extra))) for c, row in cert['gaps']))


def upper_length(cert, lengths):
    return cert['base_cost']+sum(b*(length-1) for b, length in zip(cert['beta'], lengths))


def expanded_state(state, lengths):
    result = []
    j = 0
    for value in state:
        if value:
            result.append(value)
        else:
            assert lengths[j] >= 1
            result.extend([0]*lengths[j])
            j += 1
    assert j == len(lengths)
    return tuple(result)


def lifted_word(state, word, lengths):
    """Literal macro implementation, independent of the length formula."""
    atoms, r = tagged(state)
    assert len(lengths) == r and min(lengths, default=1) >= 1
    pieces = []
    for letter in word:
        if letter == 'L':
            length = lengths[-atoms[0]-1] if atoms[0] < 0 else 1
            pieces.append('L'*length)
            atoms = atoms[1:]+atoms[:1]
        elif letter == 'R':
            length = lengths[-atoms[-1]-1] if atoms[-1] < 0 else 1
            pieces.append('R'*length)
            atoms = atoms[-1:]+atoms[:-1]
        else:
            assert letter == 'X' and not (atoms[0] < 0 and atoms[1] < 0)
            if atoms[0] < 0:
                length = lengths[-atoms[0]-1]
                pieces.append('L'*(length-1)+'X'+'RX'*(length-1))
            elif atoms[1] < 0:
                length = lengths[-atoms[1]-1]
                pieces.append('X'+'LX'*(length-1)+'R'*(length-1))
            else:
                pieces.append('X')
            atoms[0], atoms[1] = atoms[1], atoms[0]
    return cancel_rotations(''.join(pieces))


def checked_lift(state, word, lengths):
    cert = certificate(state, word)
    m = max(state, default=0)
    assert cert['final'] == tuple(range(1, m+1))+(0,)*cert['zeros']
    result = lifted_word(state, word, lengths)
    assert len(result) == exact_length(cert, lengths) == upper_length(cert, lengths)
    assert replay(expanded_state(state, lengths), result) == tuple(range(1, m+1))+(0,)*sum(lengths)
    return result


def circle_length(cert, lengths, base_n):
    extra = [length-1 for length in lengths]
    n = base_n+sum(extra)
    cost = cert['x_count']+2*sum(a*z for a, z in zip(cert['zero_swaps'], extra))
    for c, row in cert['gaps']:
        d = (c+sum(v*z for v, z in zip(row, extra))) % n
        cost += min(d, n-d)
    return cost


def checked_circle_lift(state, word, lengths):
    from multiset_phase_service import shorten_circle_runs
    lifted = checked_lift(state, word, lengths)
    start = expanded_state(state, lengths)
    result = shorten_circle_runs(lifted, len(start))
    assert len(result) == circle_length(certificate(state, word), lengths, len(state))
    m = max(state, default=0)
    assert replay(start, result) == tuple(range(1, m+1))+(0,)*sum(lengths)
    return result
