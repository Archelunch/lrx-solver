"""Build the frozen v3 instance partition and screen subset (SPEC-track1.md section 2).

    python autoresearch/sort-m9-v3-260925/build_instances.py

Reads sort-m9-260925/frozen/development.json after checking its hash against that
manifest; writes frozen-v3/{instances.json, screen-ids.json, manifest.json}.
Deterministic; refuses to overwrite existing files. No candidate code runs.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integrations.sort_loop3 import build_instances, build_screen  # noqa: E402

SOURCE = ROOT / "autoresearch" / "sort-m9-260925" / "frozen" / "manifest.json"
OUT = Path(__file__).resolve().parent / "frozen-v3"
RULE = ("Instances: for each r in 1..5, sort that r's 300 development states by (d, id) and cut them into 6 "
        "consecutive groups of 50 named r{r}-s{k}, k=1 lowest d. Screen: for each r, every state at the table "
        "radius (d == budget), then evenly spaced picks from the remaining states in (d, id) order, index "
        "int(step*i + step/2) with step = len(rest)/need, up to 20 per r.")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads(SOURCE.read_text())
    dev_path = SOURCE.parent / "development.json"
    dev_bytes = dev_path.read_bytes()
    if sha(dev_bytes) != manifest["files"]["development.json"]:
        raise SystemExit("development.json hash differs from its frozen manifest")
    states = json.loads(dev_bytes)["states"]
    instances = build_instances(states)
    screen = build_screen(states)
    files = {"instances.json": {"schema": "lrx-sort-instances-v1", "instances": instances},
             "screen-ids.json": {"schema": "lrx-sort-screen-v1", "ids": screen}}
    OUT.mkdir(exist_ok=True)
    targets = [OUT / n for n in list(files) + ["manifest.json"]]
    if any(p.exists() for p in targets):
        raise SystemExit("refusing to overwrite existing frozen-v3 files")
    for name, obj in files.items():
        (OUT / name).write_text(json.dumps(obj, indent=1) + "\n")
    out = {"schema": "lrx-sort-frozen-v3-manifest-v1", "source_manifest": str(SOURCE.relative_to(ROOT)),
           "source_manifest_sha256": sha(SOURCE.read_bytes()), "development_sha256": sha(dev_bytes),
           "instances_sha256": sha((OUT / "instances.json").read_bytes()),
           "screen_sha256": sha((OUT / "screen-ids.json").read_bytes()),
           "counts": {"instances": len(instances), "states_per_instance": sorted({len(v) for v in instances.values()}),
                      "screen": len(screen)}, "rule": RULE}
    (OUT / "manifest.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
