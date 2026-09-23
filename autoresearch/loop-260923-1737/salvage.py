"""Re-evaluate paid edits rejected by the old guard; separate from the comparison."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from integrations.eval_cache import evaluate_cached
from src.lrx.candidates import Candidate
from src.lrx.evolve import Campaign
from src.lrx.proposers import edit_violation
from src.lrx.trace import load_run


def main():
    directory = Path(__file__).parent
    assert all(load_run(p)["complete"] for p in directory.glob("*-run"))
    output = directory / "salvage-results.json"
    if output.exists():
        raise FileExistsError(output)
    rows = []
    for row in json.loads((directory / "rejected-edits.json").read_text()):
        error = edit_violation(row["parent"], row["spec"])
        result = {"run": row["run"], "id": row["id"], "guard_error": error}
        if error is None:
            candidate = Candidate(row["spec"])
            evaluation = evaluate_cached(row["spec"], cache_dir=directory / "eval-cache")
            result.update(hash=candidate.hash, ratio_rank=Campaign.ratio_rank({"eval": evaluation}),
                          score=evaluation["score"], evaluation=evaluation)
            (directory / f"salvaged-{candidate.hash}.json").write_text(
                json.dumps(row["spec"], indent=2) + "\n")
        rows.append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "evaluation"}), flush=True)
    output.write_text(json.dumps({"new_api_spend": 0, "results": rows,
        "scope": "Post-comparison train-only salvage; never credited to a frozen engine arm."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
