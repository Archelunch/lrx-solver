"""Initialize a new development archive from the audited all-cuts control.

This script never copies historical archive rows and never touches confirmation.
"""

import hashlib
import json
from pathlib import Path

from integrations.research_archive import DevelopmentArchive


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "frozen/allcuts_seed.py"
EVALUATION = ROOT / "autoresearch/loop-260924-live/offline-allcuts/3fcc0f0d23ced3f0-evaluation.json"
ARCHIVE = HERE / "development-archive.sqlite"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if ARCHIVE.exists():
        raise FileExistsError("new protocol archive already exists")
    evaluation = json.loads(EVALUATION.read_text())
    if evaluation["candidate_hash"] != sha(SOURCE):
        raise ValueError("audited source hash mismatch")
    archive = DevelopmentArchive(ARCHIVE)
    try:
        row_id = archive.add(
            run_id="protocol-incumbent", engine="deterministic_control",
            source=SOURCE.read_text(), score=evaluation["combined_score"],
            feedback={"summary": evaluation["feedback"], "certified": evaluation["certified"],
                      "new_vs_fixed_catalog": evaluation["new_certified"],
                      "limitations": evaluation["limitations"]},
            traces=evaluation["families"],
            provenance={"role": "incumbent", "source_path": str(SOURCE.relative_to(ROOT)),
                        "source_sha256": sha(SOURCE),
                        "evaluation_path": str(EVALUATION.relative_to(ROOT)),
                        "evaluation_sha256": sha(EVALUATION),
                        "selection": "audited deterministic development control; no LLM attribution"},
            claim_status="finite_development")
        print(json.dumps({"archive": str(ARCHIVE.relative_to(ROOT)), "row_id": row_id,
                          "source_sha256": sha(SOURCE), "evaluation_sha256": sha(EVALUATION)},
                         indent=2, sort_keys=True))
    finally:
        archive.close()


if __name__ == "__main__":
    main()
