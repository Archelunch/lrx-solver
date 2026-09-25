"""Independently replay the seven-gap -> five-gap (Lemma 4) projection that
the package's own coverage npz claims certifies k5-mask302-order15713.

Read-only against package/. Runs the package's own trusted verification
library functions (project_deleting_zeros, compare_word, certificate --
deterministic math, not candidate-search code) on the literal mixture rows
found via the coverage npz witness, for OUR exact mask/order/labels, and
checks criterion (7) with fractions.Fraction.
"""
import json
import sys
from fractions import Fraction
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "package"
sys.path.insert(0, str(PKG / "scripts"))

from multiset_zero_projection import project_deleting_zeros  # noqa: E402
from multiset_zero_stretch import certificate, cancel_rotations  # noqa: E402
from audit_multiset_nine_gap_cover import compare_word, literal  # noqa: E402

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


def main():
    bundle = json.loads((PKG / "literature" /
        "multiset_seven_gap_complement_certificates_20260924.json").read_text())
    assert bundle["blocks"] == 7
    record = bundle["records"][WITNESS_RECORD]
    assert record["mask"] == PARENT_MASK
    assert record["order_index"] == ORDER_INDEX
    assert record["labels"] == OUR_LABELS

    slots = [j for j in range(9) if PARENT_MASK >> j & 1]
    assert len(slots) == 7
    child_bits = {j for j in range(9) if CHILD_MASK >> j & 1}
    deleted_local = [i for i, gap in enumerate(slots) if gap not in child_bits]
    assert len(deleted_local) == 2

    target_state = state_for(OUR_LABELS, CHILD_MASK)
    weights = [Fraction(item["weight"]) for item in record["mixture"]]
    assert sum(weights) == 1 and all(w > 0 for w in weights)

    mean_base = Fraction(0)
    mean_beta = [Fraction(0)] * CHILD_MASK.bit_count()
    rows = []
    for item, weight in zip(record["mixture"], weights):
        source = bundle["catalog"][item["source"]]
        state = tuple(source["state"])
        word = source["word"]

        projected_initial, projected_word = project_deleting_zeros(
            state, word, deleted_local)
        assert len(projected_initial) == len(target_state) == 13

        # unit-length cut projection (all block lengths = 1)
        cursor, zero_ord = 0, 0
        for x in state[:item["cut"]]:
            if x:
                cursor += 1
            else:
                if zero_ord not in deleted_local:
                    cursor += 1
                zero_ord += 1
        cut = cursor % len(projected_initial)

        final_word = compare_word(target_state, projected_word, cut)
        sorted_state = literal(target_state, final_word)
        assert sorted_state == tuple(range(1, 9)) + (0,) * 5, sorted_state

        cert = certificate(target_state, cancel_rotations(final_word))
        assert cert["zeros"] == 5
        mean_base += weight * cert["base_cost"]
        mean_beta = [a + weight * b for a, b in zip(mean_beta, cert["beta"])]
        rows.append(dict(source=item["source"], cut=item["cut"], weight=str(weight),
                          word_len=len(final_word), base_cost=cert["base_cost"],
                          beta=list(cert["beta"])))

    threshold_base = 31 + 6 * CHILD_MASK.bit_count()
    ok_base = mean_base < threshold_base
    ok_beta = all(b <= 6 for b in mean_beta)
    result = dict(
        family="k5-mask302-order15713", parent_witness_record=WITNESS_RECORD,
        parent_mask=PARENT_MASK, child_mask=CHILD_MASK,
        rows=rows, mean_base=str(mean_base), threshold_base=threshold_base,
        base_ok=ok_base, mean_beta=[str(b) for b in mean_beta],
        beta_ok=ok_beta, criterion_7_certifies_all_positive_lengths=ok_base and ok_beta,
    )
    out = Path(__file__).resolve().parent / "replay-projection-result.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
