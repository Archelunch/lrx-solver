"""Offline smoke of one (arm, seed) through two mock ports (flash and reflection). No provider calls.

    python autoresearch/sort-m9-v3-260925/run_smoke.py ARM SEED ITERATIONS NAME [PREVIOUS_NAME]

With PREVIOUS_NAME, the first-prompt hashes captured there are passed as the expected hashes
(pre-send guard for GEPA/sequential, post-run ledger check for AdaEvolve/EvoX).

Writes NAME/ (under this directory): smoke configs (the campaign configs with iterations,
eval budgets and ports replaced), mock logs and captures, mock receipts, and the run
directory NAME/run. Prints the run status and the captured first-prompt hashes.
"""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main(arm, seed, iterations, name, prev=None):
    out = HERE / name
    if out.exists():
        raise SystemExit(f"refusing: {out} exists")
    out.mkdir()
    cc = json.loads((HERE / "campaign-config.json").read_text())
    fport, rport = free_port(), free_port()
    cc["broker_port"], cc["reflection"]["broker_port"] = fport, rport
    cc["reflection"]["broker_config"] = str(out / "broker-config-reflection.json")
    for key, eng in cc["engines"].items():
        eng.update(iterations=iterations, wall_seconds=1800, max_requests=iterations + 5)
        if key == "gepa":
            eng["max_metric_calls"] = 30 + (iterations + 1) * 36
        else:
            eng.update(max_screen_evals=iterations + 5, max_full_evals=iterations + 5)
    cc["eval_cache"] = "autoresearch/sort-m9-v3-260925/smoke-eval-cache"
    cc["smoke_note"] = f"smoke copy: iterations {iterations}, ports {fport}/{rport}, budgets scaled down"
    (out / "campaign-config.json").write_text(json.dumps(cc, indent=1) + "\n")
    for f in ("broker-config.json", "broker-config-reflection.json"):
        (out / f).write_text((HERE / f).read_text())
    mocks = []
    for label, port in (("flash", fport), ("reflection", rport)):
        cmd = [sys.executable, str(HERE / "mock_api.py"), str(port), str(out / f"mock-{label}.jsonl"),
               str(out / f"capture-{label}"), str(out / f"ledger-{label}.json")]
        mocks.append(subprocess.Popen(cmd, cwd=ROOT))
    try:
        for port in (fport, rport):
            for _ in range(100):
                try:
                    urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=1).read()
                    break
                except OSError:
                    time.sleep(0.1)
        cmd = [sys.executable, "-m", "integrations.sort_loop3", "run", "--engine", arm, "--seed", str(seed),
               "--run-dir", str(out / "run"), "--campaign-config", str(out / "campaign-config.json"),
               "--broker-config", str(out / "broker-config.json"),
               "--reflection-config", str(out / "broker-config-reflection.json"),
               "--broker-url", f"http://127.0.0.1:{fport}/v1", "--reflection-url", f"http://127.0.0.1:{rport}/v1",
               "--ledger", str(out / "ledger-flash.json"), "--reflection-ledger", str(out / "ledger-reflection.json")]
        if prev:
            fp = json.loads((HERE / prev / "smoke-summary.json").read_text())["first_prompts"]
            for flag, key in (("--expected-first-prompt-sha256", "solution"), ("--expected-diagnosis-sha256", "diagnosis")):
                if fp.get(key):
                    cmd += [flag, fp[key]]
        start = time.time()
        with (out / "driver-console.log").open("w") as log:
            code = subprocess.call(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        hashes = subprocess.run([sys.executable, "-m", "integrations.sort_loop3", "first-prompt", "--capture-dir",
                                 str(out / "capture-flash"), "--reflection-capture-dir", str(out / "capture-reflection"),
                                 "--all-solutions"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    finally:
        for p in mocks:
            p.terminate()
            p.wait()
    man = out / "run" / "manifest.json"
    m = json.loads(man.read_text()) if man.is_file() else {}
    summary = {"arm": arm, "seed": seed, "iterations": iterations, "exit": code, "seconds": round(time.time() - start),
               "status": m.get("status"), "research_status": m.get("research_status"),
               "seed_full": (m.get("seed_result") or {}).get("combined_score"),
               "seed_screen": (m.get("seed_screen_result") or {}).get("combined_score"),
               "best_full": (m.get("verified_best_result") or {}).get("combined_score"),
               "verifier_usage": m.get("verifier_usage"), "revealed": len(m.get("revealed_ids") or []),
               "first_prompts": json.loads(hashes) if hashes else None,
               "leak": m.get("strategy_evolution_leak"), "records_without_full_score": m.get("records_without_full_score"),
               "console_flags": m.get("console_flags"), "first_solution_prompt_check": m.get("first_solution_prompt_check")}
    (out / "smoke-summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], *sys.argv[5:6])
