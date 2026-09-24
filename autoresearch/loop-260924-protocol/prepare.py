"""Freeze a fresh structural holdout and development-only incumbent inputs.

Do not run candidate evaluation on confirmation here. Existing files are
never overwritten. The source inventory and catalog are fixed historical
inputs; this script only materializes deterministic case and profile data.
"""

import hashlib
import json
import random
import shutil
import zipfile
from pathlib import Path

from integrations.mixture_inventory import residual_inventory
from integrations.mixture_policy import ORDERS, catalog_profiles


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT / "autoresearch/official-integration-260924/frozen"
LIVE = ROOT / "autoresearch/loop-260924-live"
SOURCE = ROOT / "autoresearch/loop-260923-2107/incoming/verification.zip"
CYCLE = ROOT / "downloads/LRX_CYCLE7_8193_FAMILIES_2026-09-24/runs/cycle7/certificates.json"
PRIOR = [ROOT / f"autoresearch/{session}/{role}.json"
         for session, roles in (
             ("loop-260923-2154", ("train", "confirmation", "train-v2", "confirmation-v2")),
             ("loop-260924-optimizer", ("train", "confirmation", "baseline-cases")))
         for role in roles] + [OLD / "development.json", OLD / "confirmation.json"]
ALLCUTS = LIVE / "allcuts_seed.py"
ALLCUTS_EVALUATION = LIVE / "offline-allcuts/3fcc0f0d23ced3f0-evaluation.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def prepare():
    frozen = HERE / "frozen"
    if frozen.exists() and any(frozen.iterdir()):
        raise FileExistsError("frozen inputs already exist")
    frozen.mkdir(parents=True, exist_ok=True)
    excluded = set()
    for path in PRIOR:
        for case in json.loads(path.read_text()):
            order_index = case.get("order_index")
            if order_index is None:
                order_index = ORDERS.index(tuple(case["labels"]))
            excluded.add((case["mask"], order_index))
    prior_count = len(excluded)
    cycle = json.loads(CYCLE.read_text())
    excluded.update((case["mask"], case["order_index"]) for case in cycle["cases"])
    cycle_union_count = len(excluded)
    residual = residual_inventory(SOURCE)
    rng = random.Random(2026092402)
    confirmation = []
    for blocks in range(4, 8):
        masks = [mask for mask in sorted(residual) if mask.bit_count() == blocks]
        if not masks:
            raise ValueError("no residual masks for block count")
        while sum(case["blocks"] == blocks for case in confirmation) < 4:
            mask = rng.choice(masks)
            order_index = rng.randrange(40320)
            pair = (mask, order_index)
            if pair in excluded or not residual[mask] >> order_index & 1:
                continue
            excluded.add(pair)
            confirmation.append({"id": f"k{blocks}-mask{mask}-order{order_index}",
                                 "m": 8, "labels": list(ORDERS[order_index]),
                                 "mask": mask, "blocks": blocks})

    with zipfile.ZipFile(SOURCE) as archive:
        bundle = json.loads(archive.read(
            "literature/multiset_nine_gap_complete_certificates_20260924.json"))
    pool = json.loads((OLD / "manifest.json").read_text())["catalog_sources"]
    baseline = {}
    for case in confirmation:
        profiles = catalog_profiles({**case, "order_index": ORDERS.index(tuple(case["labels"]))}, bundle, pool)
        profiles.sort(key=lambda p: (p["base"], sum(p["gamma"]), p["gamma"]))
        baseline[case["id"]] = profiles[:64]
    for name in ("development.json", "development-baseline.json"):
        shutil.copyfile(OLD / name, frozen / name)
    shutil.copyfile(ALLCUTS, frozen / "allcuts_seed.py")
    write_new(frozen / "confirmation.json", confirmation)
    write_new(frozen / "confirmation-baseline.json", baseline)

    evaluation = json.loads(ALLCUTS_EVALUATION.read_text())
    incumbent = {family["case"]["id"]: [item["profile"] for item in family["accepted_words"]]
                 for family in evaluation["families"]}
    development_ids = {case["id"] for case in json.loads((frozen / "development.json").read_text())}
    if set(incumbent) != development_ids:
        raise ValueError("all-cuts evaluation does not match frozen development")
    write_new(frozen / "development-incumbent.json", incumbent)
    write_new(frozen / "development-dual.json", {
        "k5-mask302-order15713": {
            "tight": [1, 2, 3, 4], "mu": ["11/14", "197/196", "1/8", "261/392"],
            "nu": "30221/392", "scope": "fixed_catalog_plus_allcuts_incumbent_finite_pool",
            "status": "development_filter_only",
        }})
    file_names = ["development.json", "development-baseline.json", "allcuts_seed.py",
                  "development-incumbent.json", "development-dual.json",
                  "confirmation.json", "confirmation-baseline.json"]
    manifest = {
        "protocol": "next_iteration_structural_holdout_v1", "seed": 2026092402,
        "development_count": 16, "confirmation_count": 16,
        "confirmation_blocks": {str(i): 4 for i in range(4, 8)},
        "catalog_sources": pool, "prior_pair_count": prior_count,
        "prior_plus_cycle7_pair_count": cycle_union_count,
        "confirmation_pair_overlap_with_exclusions": 0,
        "confirmation_policy": "sealed one-shot after finalist freeze; never supplied to proposer or archive",
        "sources": {str(path.relative_to(ROOT)): sha(path)
                    for path in [SOURCE, CYCLE, *PRIOR, OLD / "manifest.json", ALLCUTS, ALLCUTS_EVALUATION]},
        "files": {name: sha(frozen / name) for name in file_names},
    }
    write_new(frozen / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2, sort_keys=True))
