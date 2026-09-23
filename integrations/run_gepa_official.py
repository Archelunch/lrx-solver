"""Run the official GEPA `optimize_anything` on an lrx-lab campaign config.

Uses the external venv (gepa is not a verifier dependency):

    .venv-ext/bin/python integrations/run_gepa_official.py campaigns/grok-rules-gepa.json \
        --allow-network --proposals 20

Multi-task mode: dataset = train graph ids; the evaluator scores one graph at a
time (sanity tier always included as a gate) and returns lrx-lab's compact
feedback as GEPA's side information. The reflection LM is our ChatClient, so
the campaign's spend ledger and request caps apply. `--fake-lm` swaps in the
offline mutator to test the wiring without network.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gepa.optimize_anything import (  # noqa: E402
    EngineConfig,
    GEPAConfig,
    ReflectionConfig,
    optimize_anything,
)

from integrations.lrx_eval import evaluate_instance, evaluate_text  # noqa: E402
from src.lrx import prompt  # noqa: E402
from src.lrx.evaluator import load_registry  # noqa: E402


class LedgerLM:
    """GEPA LanguageModel backed by lrx-lab's ChatClient (spend-capped)."""

    def __init__(self, client, kinds):
        self.client = client
        self.system = prompt.system_prompt(kinds)
        self.calls = []

    def __call__(self, request):
        if isinstance(request, str):
            messages = [{"role": "user", "content": request}]
        else:
            messages = list(request)
        messages = [{"role": "system", "content": self.system}] + messages
        out = self.client.complete(messages)
        self.calls.append(
            {k: out[k] for k in ("tokens_in", "tokens_out", "cost_usd", "seconds")}
        )
        return out["text"]


class FakeLM:
    """Offline stand-in: mutates the JSON found in GEPA's prompt."""

    def __init__(self, seed=0):
        from src.lrx.proposers import OfflineMutator

        self.mutator = OfflineMutator(seed)
        self.calls = []

    def __call__(self, request):
        text = request if isinstance(request, str) else request[-1]["content"]
        start = text.find('{"kind"')
        spec = json.JSONDecoder().raw_decode(text[start:])[0]
        out = self.mutator.propose(
            "exploit", [(spec, {})], [spec["kind"]], seed=len(self.calls)
        )
        self.calls.append({"cost_usd": 0.0})
        return "```\n" + json.dumps(out["spec"]) + "\n```"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--fake-lm", action="store_true")
    parser.add_argument("--proposals", type=int, default=10)
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    kinds = cfg.get("kinds", ["rules"])
    seed = Path(ROOT / cfg["seeds"][0]).read_text()
    stamp = time.strftime("%y%m%d-%H%M%S")
    run_dir = Path(
        args.run_dir or ROOT / "runs" / f"gepa-official-{cfg.get('name', 'x')}-{stamp}"
    )
    if run_dir.exists():
        raise FileExistsError(run_dir)
    run_dir.mkdir(parents=True)

    if args.fake_lm:
        lm = FakeLM(cfg.get("seed", 0))
    else:
        from src.lrx.evolve import build_proposer

        proposer = build_proposer(cfg, args.allow_network)
        lm = LedgerLM(proposer.client, kinds)

    train = [
        f"m{g['m']}r{g['r']}" for g in load_registry()["graphs"] if g["role"] == "train"
    ]

    def evaluator(candidate, example=None):
        return evaluate_instance(candidate, example)

    result = optimize_anything(
        seed_candidate=seed,
        evaluator=evaluator,
        dataset=train,
        objective=(
            "Improve this JSON candidate for the LRX sorting problem. Reply with ONE "
            "JSON candidate in a fenced block, following the DSL in the system prompt. "
            "Maximise score (0 is ideal): no failures, max word length <= T for m>=8."
        ),
        background=prompt.PROBLEM + "\n" + prompt.SCORING,
        config=GEPAConfig(
            engine=EngineConfig(
                run_dir=str(run_dir / "gepa"),
                max_candidate_proposals=args.proposals,
                seed=cfg.get("seed", 0),
                max_workers=cfg.get("eval_workers", 4),
            ),
            reflection=ReflectionConfig(reflection_lm=lm),
        ),
    )
    best = result.best_candidate
    best_text = best if isinstance(best, str) else json.dumps(best)
    score, side = evaluate_text(best_text, split="train")
    held, _ = evaluate_text(best_text, split="heldout")
    summary = {
        "run_dir": str(run_dir),
        "engine": "gepa-official",
        "proposals_cap": args.proposals,
        "lm_calls": len(lm.calls),
        "usd": round(sum(c.get("cost_usd", 0) for c in lm.calls), 6),
        "best_train_score": score,
        "best_heldout_score": held,
        "best_feasible_train": side.get("feasible_on_probes"),
        "best": best_text,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
