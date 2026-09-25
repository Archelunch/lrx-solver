"""Feed the seven-gap witness mixture, projected to mask=302 by our OWN
Lemma-4 deletion, into our repo's own evaluator path
(integrations/projected_mixtures.py: comparison() + verify_mixture()),
which is what integrations/mixture_policy.py's catalog_profiles/Evaluator
call in autoresearch/loop-260924-protocol. Does not modify src/lrx or
integrations/.
"""
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
PKG = Path(__file__).resolve().parents[1] / "package"

from integrations.projected_mixtures import comparison, verify_mixture  # noqa: E402

OUR_LABELS = [4, 1, 7, 8, 5, 6, 3, 2]
CHILD_MASK = 302
PARENT_MASK = 446
WITNESS_RECORD = 37688


def literal_step(state, c):
    if c == 'L':
        return state[1:] + state[:1]
    if c == 'R':
        return state[-1:] + state[:-1]
    return (state[1], state[0]) + tuple(state[2:])


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
    return initial, ''.join(out)


def cancel_rotations(word):
    out = []
    for c in word:
        if out and (out[-1], c) in (('L', 'R'), ('R', 'L')):
            out.pop()
        else:
            out.append(c)
    return ''.join(out)


def main():
    bundle = json.loads((PKG / "literature" /
        "multiset_seven_gap_complement_certificates_20260924.json").read_text())
    record = bundle["records"][WITNESS_RECORD]
    assert record["mask"] == PARENT_MASK and record["labels"] == OUR_LABELS

    slots = [j for j in range(9) if PARENT_MASK >> j & 1]
    child_bits = {j for j in range(9) if CHILD_MASK >> j & 1}
    deleted_local = [i for i, gap in enumerate(slots) if gap not in child_bits]

    profiles, weights, errors = [], [], []
    for item in record["mixture"]:
        source = bundle["catalog"][item["source"]]
        state = tuple(source["state"])
        word = source["word"]
        initial, projected_word = project_deleting_zeros(state, word, deleted_local)

        cursor, zero_ord = 0, 0
        for x in state[:item["cut"]]:
            if x:
                cursor += 1
            else:
                if zero_ord not in deleted_local:
                    cursor += 1
                zero_ord += 1
        cut = cursor % len(initial)

        try:
            p = comparison(initial, cancel_rotations(projected_word), cut, OUR_LABELS)
        except Exception as e:
            errors.append(dict(source=item["source"], error=str(e)))
            continue
        if p is None:
            errors.append(dict(source=item["source"], error="comparison() returned None"))
            continue
        profiles.append(p)
        weights.append(item["weight"])

    result = dict(profiles_built=len(profiles), errors=errors)
    if profiles and not errors:
        try:
            mix = verify_mixture(profiles, weights)
            result["verify_mixture"] = mix
            result["accepted_by_our_evaluator"] = True
        except Exception as e:
            result["verify_mixture_error"] = str(e)
            result["accepted_by_our_evaluator"] = False
    else:
        result["accepted_by_our_evaluator"] = False

    out = Path(__file__).resolve().parent / "evaluator-check-result.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
