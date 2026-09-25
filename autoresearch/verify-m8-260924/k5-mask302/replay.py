"""Search the verify-m8-260924 package for a certificate covering our
k5-mask302-order15713 family (mask=302, order_index=15713, m=8).

Stdlib only. Does not modify anything under package/. Streams files with
mmap instead of loading them fully into memory (the five/six-gap bounded
search files are 122-166MB).

Usage: run from the lrx-lab repo root.
    python3 autoresearch/verify-m8-260924/k5-mask302/replay.py
"""
import json
import mmap
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "package"
LIT = PKG / "literature"

MASK = 302
ORDER_INDEX = 15713
LABELS = [4, 1, 7, 8, 5, 6, 3, 2]


def find_exact_pair(path, mask=MASK, order_index=ORDER_INDEX):
    """Count all '"mask":<mask>,' records in a (possibly huge) JSON file and
    check whether any is immediately followed by '"order_index":<order_index>,'.
    Returns (total_mask_hits, found: bool, first_match_offset_or_None)."""
    pat_mask = f'"mask":{mask},'.encode()
    pat_order = f'"order_index":{order_index},'.encode()
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        pos = 0
        count = 0
        match = None
        while True:
            idx = mm.find(pat_mask, pos)
            if idx == -1:
                break
            count += 1
            if match is None and pat_order in mm[idx: idx + 80]:
                match = idx
            pos = idx + 1
        mm.close()
    return count, match is not None, match


def find_pair_by_order(path, order_index=ORDER_INDEX):
    """Return list of (offset, mask_value_bytes) for every record whose
    order_index equals order_index, regardless of mask."""
    pat = f'"order_index":{order_index},'.encode()
    hits = []
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        pos = 0
        while True:
            idx = mm.find(pat, pos)
            if idx == -1:
                break
            start = max(0, idx - 40)
            hits.append((idx, mm[start:idx + 40]))
            pos = idx + 1
        mm.close()
    return hits


def main():
    results = {}

    five_gap_search = LIT / "multiset_five_gap_bounded_search_20260924.json"
    total, found, off = find_exact_pair(five_gap_search)
    results["five_gap_bounded_search"] = dict(
        file=str(five_gap_search.relative_to(PKG)),
        total_mask302_records=total, found_order15713=found, offset=off)

    six_gap_search = LIT / "multiset_six_gap_bounded_search_20260924.json"
    hits = find_pair_by_order(six_gap_search)
    six_masks = []
    for off, ctx in hits:
        s = ctx.decode("utf-8", "replace")
        m = s.split('"mask":')[-1].split(",")[0]
        six_masks.append(int(m))
    supersets = [m for m in six_masks if (m & MASK) == MASK]
    results["six_gap_bounded_search"] = dict(
        file=str(six_gap_search.relative_to(PKG)),
        order15713_masks=six_masks,
        masks_that_are_bit_supersets_of_302=supersets)

    small_files = [
        "multiset_five_gap_bounded_repairs_final_20260924.json",
        "multiset_five_gap_repairs_final_audit_20260924.json",
        "multiset_five_gap_control_seed_20260924.jsonl",
        "multiset_six_gap_bounded_repairs_final_20260924.json",
        "multiset_six_gap_bounded_repair_prefix_20260924.json",
        "multiset_six_gap_bounded_repair_prefix2_20260924.json",
        "multiset_seven_gap_complement_certificates_20260924.json",
        "multiset_eight_gap_complement_certificates_20260924.json",
    ]
    for name in small_files:
        p = LIT / name
        if not p.exists():
            results[name] = "missing"
            continue
        text = p.read_text(errors="replace")
        results[name] = dict(
            order_index_15713_occurrences=text.count('"order_index":15713'))

    coverage_npz = LIT / "multiset_five_gap_complete_coverage_20260924.npz"
    results["coverage_npz_present"] = coverage_npz.exists()

    audit = json.loads((LIT / "multiset_five_gap_complete_audit_20260924.json").read_text())
    results["complete_audit_claims"] = dict(
        status=audit["status"],
        complete_five_gap_proved=audit["complete_five_gap_proved"],
        full_m8_proved=audit["full_m8_proved"],
        source_input=audit["source_input"],
        references_missing_coverage_npz=(
            "literature/multiset_five_gap_complete_coverage_20260924.npz"
            in audit["source_sha256"]))

    out = Path(__file__).resolve().parent / "replay-result.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
