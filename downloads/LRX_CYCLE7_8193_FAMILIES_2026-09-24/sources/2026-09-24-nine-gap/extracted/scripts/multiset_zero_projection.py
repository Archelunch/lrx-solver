"""Delete selected physically tracked zero tokens from an LRX word.

The result follows from a one-generator projection identity, independently
of any distance bound or route constructor. Zero indices refer to their
left-to-right order in the initial state, not to their later positions.
"""


def literal_step(state, letter):
    if letter == 'L':
        return state[1:] + state[:1]
    if letter == 'R':
        return state[-1:] + state[:-1]
    assert letter == 'X' and len(state) >= 2
    return (state[1], state[0]) + state[2:]


def project_deleting_zeros(state, word, deleted, *, check_every_step=False):
    deleted = frozenset(deleted)
    state = tuple(state)
    count = state.count(0)
    assert all(isinstance(j, int) and 0 <= j < count for j in deleted)
    assert len(state) - len(deleted) >= 2
    atoms, ordinal = [], 0
    for value in state:
        assert value >= 0
        if value:
            atoms.append(value)
        else:
            atoms.append(-ordinal - 1)
            ordinal += 1
    atoms = tuple(atoms)

    def kept(x):
        return x > 0 or -x - 1 not in deleted

    def erase(a):
        return tuple(max(x, 0) for x in a if kept(x))

    source = projected = erase(atoms)
    output = []
    for letter in word:
        if letter == 'L':
            emit = kept(atoms[0])
        elif letter == 'R':
            emit = kept(atoms[-1])
        else:
            assert letter == 'X'
            emit = kept(atoms[0]) and kept(atoms[1])
        atoms = literal_step(atoms, letter)
        if emit:
            output.append(letter)
            projected = literal_step(projected, letter)
        if check_every_step:
            assert projected == erase(atoms)
    assert projected == erase(atoms)
    return source, ''.join(output)
