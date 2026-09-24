"""Freeze fresh 4..7-block residual families and direct catalog profiles.

This is a preparation script, not a candidate evaluator. Rerun only into an
empty output directory; existing evidence is never overwritten.
"""

import argparse
import hashlib
import json
import random
import zipfile
from pathlib import Path

from integrations.mixture_inventory import residual_inventory
from integrations.mixture_policy import ORDERS, catalog_profiles

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "autoresearch/loop-260923-2107/incoming/verification.zip"
CYCLE = ROOT / "downloads/LRX_CYCLE7_8193_FAMILIES_2026-09-24/runs/cycle7/certificates.json"
PRIOR = [ROOT / f"autoresearch/{session}/{role}.json"
         for session, roles in (
             ("loop-260923-2154", ("train", "confirmation", "train-v2", "confirmation-v2")),
             ("loop-260924-optimizer", ("train", "confirmation", "baseline-cases")))
         for role in roles]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(out_dir, *, seed=20260924, development_per_block=4,
            confirmation_per_block=2, catalog_sources=48):
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError("fresh output directory required")
    out_dir.mkdir(parents=True, exist_ok=True)
    excluded = set()
    for path in PRIOR:
        for case in json.loads(path.read_text()):
            excluded.add((case["mask"], case["order_index"]))
    cycle = json.loads(CYCLE.read_text())
    excluded.update((case["mask"], case["order_index"]) for case in cycle["cases"])
    residual = residual_inventory(SOURCE)
    rng = random.Random(seed)
    development, confirmation = [], []
    for blocks in range(4, 8):
        masks = [mask for mask in sorted(residual) if mask.bit_count() == blocks]
        if not masks:
            raise ValueError("no residual masks for block count")
        for role, count in ((development, development_per_block),
                            (confirmation, confirmation_per_block)):
            while sum(c["blocks"] == blocks for c in role) < count:
                mask = rng.choice(masks)
                order_index = rng.randrange(40320)
                pair = (mask, order_index)
                if pair in excluded or not residual[mask] >> order_index & 1:
                    continue
                excluded.add(pair)
                role.append(dict(id=f"k{blocks}-mask{mask}-order{order_index}",
                                 m=8, labels=list(ORDERS[order_index]), mask=mask,
                                 blocks=blocks))
    with zipfile.ZipFile(SOURCE) as archive:
        bundle = json.loads(archive.read(
            "literature/multiset_nine_gap_complete_certificates_20260924.json"))
    pool = list(range(len(bundle["catalog"])))
    random.Random(seed + 1).shuffle(pool)
    pool = pool[:catalog_sources]

    def baseline_for(cases):
        baseline = {}
        for case in cases:
            order_index = ORDERS.index(tuple(case["labels"]))
            profiles = catalog_profiles({**case, "order_index": order_index}, bundle, pool)
            # Keep a deterministic, bounded support while retaining varied
            # block coefficients. This is a fixed direct profile baseline.
            profiles.sort(key=lambda p: (p["base"], sum(p["gamma"]), p["gamma"]))
            baseline[case["id"]] = profiles[:64]
        return baseline

    for name, value in (("development.json", development),
                        ("confirmation.json", confirmation),
                        ("development-baseline.json", baseline_for(development)),
                        ("confirmation-baseline.json", baseline_for(confirmation))):
        (out_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    manifest = dict(seed=seed, m=8, blocks=list(range(4, 8)),
                    development_count=len(development), confirmation_count=len(confirmation),
                    catalog_sources=pool, residual_scope="source projection residual",
                    exclusion_count=len(excluded),
                    sources={str(path.relative_to(ROOT)): sha(path) for path in [SOURCE, CYCLE, *PRIOR]},
                    files={name: sha(out_dir / name) for name in (
                        "development.json", "confirmation.json",
                        "development-baseline.json", "confirmation-baseline.json")},
                    confirmation_policy="one shot after development, never passed to proposer")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
