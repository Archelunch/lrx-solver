"""Native GEPA acceptance check with explicitly synthetic sub-certificate grades.

This is an optimizer plumbing test, not evidence of an LRX profile improvement.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything
from integrations.official_backends import HardCaseBatchSampler


class ScriptedLM:
    def __init__(self):
        self.calls = 0

    def __call__(self, _request):
        self.calls += 1
        return "```python\ndef propose_words(case):\n    return []\n# fixture-grade-%d\n```" % self.calls


def main():
    run_dir = Path(__file__).parent / "offline-gepa-graded"
    if run_dir.exists():
        raise FileExistsError(run_dir)
    seed = "def propose_words(case):\n    return []\n# fixture-grade-0\n"
    cases = [{"id": "hard"}, {"id": "solved-a"}, {"id": "solved-b"}]
    lm = ScriptedLM()

    def evaluator(candidate, example):
        grade = int(candidate.split("fixture-grade-")[1].split()[0])
        if example["id"] == "hard":
            score = grade / 10
        else:
            score = 1.0
        return score, {"feedback": "Synthetic graded progress only; no LRX certificate"}

    result = optimize_anything(
        seed_candidate=seed, evaluator=evaluator, dataset=cases,
        objective="Return a complete Python source with one higher fixture-grade comment.",
        background="Offline synthetic acceptance test only.",
        config=GEPAConfig(
            engine=EngineConfig(run_dir=str(run_dir), seed=0,
                                max_candidate_proposals=2, max_metric_calls=100,
                                max_workers=1, parallel=False),
            reflection=ReflectionConfig(reflection_lm=lm,
                                        batch_sampler=HardCaseBatchSampler({"hard"})),
        ),
    )
    rows = json.loads((run_dir / "run_log.json").read_text())
    summary = {"calls": lm.calls, "sampled_ids": [row["subsample_ids"] for row in rows],
               "before": [row["subsample_scores"] for row in rows],
               "after": [row["new_subsample_scores"] for row in rows],
               "best_grade": int(result.best_candidate.split("fixture-grade-")[1].split()[0]),
               "warning": "synthetic scores only; no LRX mathematical progress"}
    (run_dir / "fixture-report.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
