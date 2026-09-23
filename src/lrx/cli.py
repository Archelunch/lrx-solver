"""Offline-first bounded command-line experiments."""

import argparse
import json
import random
import sys

from .certificates import CertificateValidator, verify_family, verify_family_distance
from .commands import COMMANDS
from .commands import main as commands_main
from .evaluate import evaluate_projection
from .reference_bfs import bfs_visible
from .state import distance_upper_bound, state_counts, state_from_vector


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in COMMANDS:
        try:
            return commands_main(argv)
        except (ValueError, OSError, RuntimeError) as exc:
            print(json.dumps({"status": "ERROR", "reason": str(exc)}), file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("info", "bfs", "projection", "experiment", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("m", type=int)
        sub.add_argument("r", type=int)
        if name == "bfs":
            sub.add_argument("--max-vertices", type=int, default=100_000)
        elif name == "projection":
            sub.add_argument("--q", type=int)
            sub.add_argument("--max-cells", type=int, default=1_000_000)
        elif name == "experiment":
            sub.add_argument(
                "--mode",
                choices=["baseline", "best_of_n", "sequential", "parallel"],
                default="best_of_n",
            )
            sub.add_argument("--proposals", type=int, default=8)
            sub.add_argument("--seed", type=int, default=42)
            sub.add_argument("--samples", type=int, default=12)
            sub.add_argument("--output")
            sub.add_argument("--max-work", type=int, default=1_000_000)
            sub.add_argument(
                "--provider", choices=["offline", "xai"], default="offline"
            )
            sub.add_argument("--allow-network", action="store_true")
            sub.add_argument("--base-url", default="https://api.x.ai/v1")
            sub.add_argument("--model", default="grok-4.7")
            sub.add_argument("--api-key-env", default="XAI_API_KEY")
            sub.add_argument("--max-requests", type=int, default=20)
            sub.add_argument("--max-output-tokens", type=int, default=200)
            sub.add_argument("--max-spend", type=float)
            sub.add_argument(
                "--input-price", type=float, help="Current USD per million input tokens"
            )
            sub.add_argument(
                "--output-price",
                type=float,
                help="Current USD per million output tokens",
            )
        elif name == "verify":
            sub.add_argument("word")
            sub.add_argument(
                "--start", required=True, help="Comma-separated starting vector"
            )
            sub.add_argument("--mark", type=int, required=True)
    family = commands.add_parser("family")
    family.add_argument("k", type=int)
    family.add_argument(
        "--verify-only", action="store_true", help="Compatibility flag; no BFS is run"
    )
    family.add_argument(
        "--exact", action="store_true", help="Check bounded complete disjoint balls"
    )
    family.add_argument("--max-vertices", type=int, default=50_000)
    commands.add_parser("smoke")
    args = parser.parse_args(argv)
    try:
        code = 0
        if args.command == "family":
            result = (
                verify_family_distance(args.k, args.max_vertices)
                if args.exact
                else verify_family(args.k)
            )
            code = (
                2
                if result.get("status") == "INCOMPLETE"
                else 0
                if result["verified_upper_bound"]
                and (not args.exact or result["exact_distance"] is not None)
                else 1
            )
        elif args.command == "smoke":
            family_result = verify_family(3)
            bfs = bfs_visible(2, 2)
            result = {
                "family": family_result,
                "visible_states": len(bfs.distances),
                "passed": family_result["verified_upper_bound"]
                and bfs.status == "COMPLETE"
                and len(bfs.distances) == 12,
            }
            code = 0 if result["passed"] else 1
        elif args.command == "info":
            result = {
                "m": args.m,
                "r": args.r,
                "n": args.m + args.r,
                "counts": state_counts(args.m, args.r),
                "conjectured_budget": distance_upper_bound(args.m, args.r),
                "conjecture_domain": args.m >= 8 and args.r >= 2,
            }
        elif args.command == "bfs":
            bfs = bfs_visible(args.m, args.r, max_vertices=args.max_vertices)
            result = {
                "status": bfs.status,
                "graph": "visible canonical-root",
                "states_discovered": len(bfs.distances),
                "reason": bfs.exhaustion_reason,
                "sorting_radius": max(bfs.distances.values())
                if bfs.status == "COMPLETE"
                else None,
            }
            code = 0 if bfs.status == "COMPLETE" else 2
        elif args.command == "projection":
            result = evaluate_projection(args.m, args.r, args.q, args.max_cells)
            code = (
                2
                if result["status"] != "COMPLETE"
                else (0 if result["lifting_bound_holds_on_this_graph"] else 1)
            )
        elif args.command == "verify":
            v = tuple(int(x) for x in args.start.split(","))
            cert = CertificateValidator(args.m, args.r).replay_word(
                args.word,
                state_from_vector(v, args.mark),
                budget=distance_upper_bound(args.m, args.r),
            )
            result = cert.to_dict()
            code = 0 if cert.replay_valid and cert.terminal else 1
        else:
            from .candidate_runner import run_experiment

            proposer = None
            if args.provider == "xai":
                from .provider_adapter import BudgetLedger, XAIAdapter

                if not args.allow_network:
                    raise ValueError("Live API use requires --allow-network")
                ledger = BudgetLedger(
                    args.max_spend, args.input_price, args.output_price
                )
                proposer = XAIAdapter(
                    base_url=args.base_url,
                    model=args.model,
                    allow_network=True,
                    api_key_env=args.api_key_env,
                    max_requests=args.max_requests,
                    max_output_tokens=args.max_output_tokens,
                )
                proposer.attach_ledger(ledger)
            if not 1 <= args.samples <= 100:
                raise ValueError("Require 1..100 samples")
            if state_counts(args.m, args.r)["visible"] > 10_000:
                raise ValueError(
                    "Demo dataset cap is 10000 states; provide a research corpus through Python"
                )
            bfs = bfs_visible(args.m, args.r, max_vertices=10_000)
            states = sorted(bfs.distances)
            states = random.Random(args.seed).sample(
                states, min(args.samples, len(states))
            )
            result = run_experiment(
                args.m,
                args.r,
                states,
                mode=args.mode,
                proposals=args.proposals,
                seed=args.seed,
                output_file=args.output,
                proposer=proposer,
                max_work=args.max_work,
            )
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return code
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
