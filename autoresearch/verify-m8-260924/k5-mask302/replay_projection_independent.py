"""Fully independent stdlib replay of the k5-mask302-order15713 certificate.

No functions are imported from package/scripts or from integrations/ here;
every primitive (Lemma 4 deletion, Lemma 3 comparison transfer, Lemma 1
literal lifting) is reimplemented from scratch against the raw JSON data in
package/literature/multiset_seven_gap_complement_certificates_20260924.json
(read-only). This is the mathematically forced algorithm (0/1-principle
argument for the comparison transfer); only the code is independent, not
the underlying lemma, which follows the manuscript sections cited in the
task.
"""
import json
from fractions import Fraction
from itertools import combinations
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "package"

OUR_LABELS = [4, 1, 7, 8, 5, 6, 3, 2]
CHILD_MASK = 302
PARENT_MASK = 446
ORDER_INDEX = 15713
WITNESS_RECORD = 37688


def state_for(labels, mask):
    out = []
    for j in range(9):
        if mask >> j & 1:
            out.append(0)
        if j < 8:
            out.append(labels[j])
    return tuple(out)


def literal_step(state, c):
    if c == 'L':
        return state[1:] + state[:1]
    if c == 'R':
        return state[-1:] + state[:-1]
    assert c == 'X'
    return (state[1], state[0]) + tuple(state[2:])


def literal_run(state, word):
    for c in word:
        state = literal_step(state, c)
    return state


# ---------------- Lemma 4: delete selected zero atoms ----------------
def project_deleting_zeros(state, word, deleted):
    deleted = set(deleted)
    atoms, ordinal = [], 0
    for v in state:
        if v:
            atoms.append(v)
        else:
            atoms.append(-(ordinal + 1))
            ordinal += 1
    atoms = tuple(atoms)

    def kept(x):
        return x > 0 or (-x - 1) not in deleted

    def erase(a):
        return tuple(max(x, 0) for x in a if kept(x))

    initial = erase(atoms)
    projected = initial
    out = []
    for c in word:
        if c == 'L':
            emit = kept(atoms[0])
        elif c == 'R':
            emit = kept(atoms[-1])
        else:
            emit = kept(atoms[0]) and kept(atoms[1])
        atoms = literal_step(atoms, c)
        if emit:
            out.append(c)
            projected = literal_step(projected, c)
    assert projected == erase(atoms)
    return initial, ''.join(out)


# ---------------- Lemma 3: comparison transfer (0/1-principle) ----------------
def net_rotation(n, word):
    at = 0
    for c in word:
        if c in 'LR':
            at = (at + (1 if c == 'L' else -1)) % n
    return at


def target_ranks(target_state, cut, finish):
    n = len(target_state)
    root = tuple(range(1, 9)) + (0,) * (n - 8)
    physical = root[-finish:] + root[:-finish] if finish else root
    goal = physical[cut:] + physical[:cut]
    locations, zero_positions = {}, []
    for j, x in enumerate(goal):
        if x:
            locations[x] = j
        else:
            zero_positions.append(j)
    zero_iter = iter(zero_positions)
    shifted = target_state[cut:] + target_state[:cut]
    return [locations[x] if x else next(zero_iter) for x in shifted]


def inversions(p):
    return sum(p[i] > p[j] for i in range(len(p)) for j in range(i + 1, len(p)))


def transfer_word(target_state, word, cut):
    n = len(target_state)
    finish = net_rotation(n, word)
    p0 = target_ranks(target_state, cut, finish)
    inv0 = inversions(p0)
    p = list(p0)
    cursor = (-cut) % n
    out, swaps_done = [], 0
    for c in word:
        if c == 'X':
            assert cursor < n - 1
            if p[cursor] > p[cursor + 1]:
                p[cursor], p[cursor + 1] = p[cursor + 1], p[cursor]
                out.append('X')
                swaps_done += 1
        else:
            cursor = (cursor + (1 if c == 'L' else -1)) % n
            out.append(c)
    assert p == list(range(n)), "comparison transfer did not sort target ranks"
    assert swaps_done == inv0, (swaps_done, inv0)
    return ''.join(out), inv0


# ---------------- Lemma 1: literal zero-block lifting ----------------
def lift_word(unit_state, word, lengths):
    atoms, ordinal = [], 0
    for v in unit_state:
        if v:
            atoms.append(v)
        else:
            atoms.append(-(ordinal + 1))
            ordinal += 1
    assert len(lengths) == ordinal
    atoms = list(atoms)
    pieces = []
    for c in word:
        if c == 'L':
            h = lengths[-atoms[0] - 1] if atoms[0] < 0 else 1
            pieces.append('L' * h)
            atoms = atoms[1:] + atoms[:1]
        elif c == 'R':
            h = lengths[-atoms[-1] - 1] if atoms[-1] < 0 else 1
            pieces.append('R' * h)
            atoms = atoms[-1:] + atoms[:-1]
        else:
            if atoms[0] < 0:
                h = lengths[-atoms[0] - 1]
                pieces.append('L' * (h - 1) + 'X' + 'RX' * (h - 1))
            elif atoms[1] < 0:
                h = lengths[-atoms[1] - 1]
                pieces.append('X' + 'LX' * (h - 1) + 'R' * (h - 1))
            else:
                pieces.append('X')
            atoms[0], atoms[1] = atoms[1], atoms[0]
    return ''.join(pieces)


def cancel_rotations(word):
    out = []
    for c in word:
        if out and (out[-1], c) in (('L', 'R'), ('R', 'L')):
            out.pop()
        else:
            out.append(c)
    return ''.join(out)


def expanded_state(unit_state, lengths):
    out, j = [], 0
    for v in unit_state:
        if v:
            out.append(v)
        else:
            out.extend([0] * lengths[j])
            j += 1
    return tuple(out)


def lifted_length(unit_state, word, lengths):
    lifted = cancel_rotations(lift_word(unit_state, word, lengths))
    expected = tuple(range(1, 9)) + (0,) * sum(lengths)
    got = literal_run(expanded_state(unit_state, lengths), lifted)
    assert got == expected, (lengths, got, expected)
    return len(lifted)


def main():
    bundle = json.loads((PKG / "literature" /
        "multiset_seven_gap_complement_certificates_20260924.json").read_text())
    assert bundle["blocks"] == 7
    record = bundle["records"][WITNESS_RECORD]
    assert record["mask"] == PARENT_MASK
    assert record["order_index"] == ORDER_INDEX
    assert record["labels"] == OUR_LABELS

    slots = [j for j in range(9) if PARENT_MASK >> j & 1]
    child_bits = {j for j in range(9) if CHILD_MASK >> j & 1}
    deleted_local = [i for i, gap in enumerate(slots) if gap not in child_bits]
    assert len(deleted_local) == 2

    target_state = state_for(OUR_LABELS, CHILD_MASK)  # 13 symbols, 5 zeros
    weights = [Fraction(item["weight"]) for item in record["mixture"]]
    assert sum(weights) == 1 and all(w > 0 for w in weights)

    k = CHILD_MASK.bit_count()  # 5
    mean_base = Fraction(0)
    mean_beta = [Fraction(0)] * k
    rows = []

    for item, weight in zip(record["mixture"], weights):
        source = bundle["catalog"][item["source"]]
        state = tuple(source["state"])
        word = source["word"]

        projected_initial, projected_word = project_deleting_zeros(state, word, deleted_local)
        assert len(projected_initial) == len(target_state) == 13

        cursor, zero_ord = 0, 0
        for x in state[:item["cut"]]:
            if x:
                cursor += 1
            else:
                if zero_ord not in deleted_local:
                    cursor += 1
                zero_ord += 1
        cut = cursor % len(projected_initial)

        final_word, inv0 = transfer_word(target_state, projected_word, cut)
        assert literal_run(target_state, final_word) == tuple(range(1, 9)) + (0,) * k

        base0 = lifted_length(target_state, final_word, [1] * k)
        beta = []
        two_j = []
        for j in range(k):
            lengths_e = [1] * k
            lengths_e[j] = 2
            Lj = lifted_length(target_state, final_word, lengths_e)
            beta.append(Lj - base0)
            lengths_2e = [1] * k
            lengths_2e[j] = 3
            L2j = lifted_length(target_state, final_word, lengths_2e)
            assert L2j == base0 + 2 * beta[j], (j, L2j, base0, beta[j])
            two_j.append(L2j)
        for i, j in combinations(range(k), 2):
            lengths_ij = [1] * k
            lengths_ij[i] = 2
            lengths_ij[j] = 2
            Lij = lifted_length(target_state, final_word, lengths_ij)
            assert Lij == base0 + beta[i] + beta[j], (i, j, Lij, base0, beta[i], beta[j])

        mean_base += weight * base0
        mean_beta = [a + weight * b for a, b in zip(mean_beta, beta)]
        rows.append(dict(source=item["source"], cut=item["cut"], weight=str(weight),
                          base=base0, beta=beta, inversions_check=inv0))

    threshold_base = 31 + 6 * k
    ok_base = mean_base < threshold_base
    ok_beta = all(b <= 6 for b in mean_beta)
    result = dict(
        rows=rows, mean_base=str(mean_base), threshold_base=threshold_base, base_ok=ok_base,
        mean_beta=[str(b) for b in mean_beta], beta_ok=ok_beta,
        criterion_7_certifies_all_positive_lengths=ok_base and ok_beta,
        matches_previous_replay=dict(
            base="121/2" == str(mean_base),
            beta=["6", "63/11", "6", "6", "6"] == [str(b) for b in mean_beta]),
    )
    out = Path(__file__).resolve().parent / "replay-projection-independent-result.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
