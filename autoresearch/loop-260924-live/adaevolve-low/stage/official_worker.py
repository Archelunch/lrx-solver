"""Run pinned upstream GEPA, SkyDiscover AdaEvolve, and EvoX on LRX programs.

The launcher stages only development inputs and evaluator code in a fresh run
directory, then confines the *whole* optimizer process with macOS Seatbelt.
This matters for EvoX: its evolved database is Python code imported by the
upstream process. Candidate programs receive a second, stricter sandbox in
``program_evaluator``. All model traffic goes to a local budget broker.
"""

from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = {
    "gepa": "gepa==0.1.4",
    "adaevolve": "skydiscover==0.2.0@0d932b690670a7e544388ad362e9876c8bd256a0",
    "evox": "skydiscover==0.2.0@0d932b690670a7e544388ad362e9876c8bd256a0",
}
SYSTEM = (
    "Find constructive LRX sorting algorithms. Candidate source must define "
    "propose_words(case), accepting a dict with m, labels, mask, id, blocks and "
    "returning a list of at most 32 strings over L,R,X, each at most 4096 "
    "characters. Source must be at most 64 KiB and finish each case within 2 "
    "seconds. Use only Python's standard library. Every returned word is "
    "independently replayed and scored. "
    "An absent word is a failed search, never a distance lower bound. "
    "Do not read files, the network, environment variables, or hidden examples."
)


def _load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    cases = data["cases"] if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases file must contain a nonempty JSON list")
    return cases


def _broker_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("broker URL must be a loopback HTTP URL")
    if not parsed.path.rstrip("/").endswith("/v1"):
        raise ValueError("broker URL must end in /v1")
    return value.rstrip("/")


def _source_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_inputs(args) -> dict:
    from tools.orchestrator import trusted_status

    trust = trusted_status()
    if not trust["ok"]:
        raise RuntimeError(f"trusted core lock mismatch: {trust}")
    manifest_path = args.frozen_manifest or args.cases.parent / "manifest.json"
    if not manifest_path.is_file():
        if not args.allow_custom_cases:
            raise FileNotFoundError("frozen manifest required; use --allow-custom-cases only for fixtures")
        return {"trusted_status": trust, "frozen_manifest": None}
    frozen = json.loads(manifest_path.read_text())
    expected = frozen.get("files", {})
    for path in (args.cases, args.baseline):
        if path is None:
            continue
        digest = expected.get(path.name)
        if digest != _source_digest(path):
            raise RuntimeError(f"frozen hash mismatch for {path}")
    if not args.allow_custom_cases and (args.cases.name != "development.json" or
                                        not args.baseline or args.baseline.name != "development-baseline.json"):
        raise ValueError("official proposer requires the frozen development pair")
    return {"trusted_status": trust, "frozen_manifest": str(manifest_path),
            "frozen_manifest_sha256": _source_digest(manifest_path)}


def _installed_identity(python: Path, engine: str) -> str:
    name = "gepa" if engine == "gepa" else "skydiscover"
    query = ("import importlib.metadata as m, json; "
             f"d=m.distribution({name!r}); "
             "print(json.dumps({'version':d.version,'url':d.read_text('direct_url.json')}))")
    proc = subprocess.run([str(python), "-c", query], capture_output=True, text=True,
                          timeout=15, check=True)
    row = json.loads(proc.stdout)
    expected_version = "0.1.4" if engine == "gepa" else "0.2.0"
    if row["version"] != expected_version:
        raise RuntimeError(f"unexpected {name} version: {row['version']}")
    if engine != "gepa":
        direct = json.loads(row["url"] or "{}")
        commit = direct.get("vcs_info", {}).get("commit_id")
        if commit != "0d932b690670a7e544388ad362e9876c8bd256a0":
            raise RuntimeError(f"unexpected SkyDiscover source commit: {commit}")
    return UPSTREAM[engine]


def _snapshot_best(best: Path, output_dir: Path, verified_dir: Path) -> Path:
    """Accept only a bounded regular output file, then freeze its bytes."""
    if not best.is_file() or not stat.S_ISREG(best.lstat().st_mode) or best.is_symlink():
        raise FileNotFoundError(f"upstream did not export a regular best program: {best}")
    if not best.resolve().is_relative_to(output_dir.resolve()) or best.stat().st_size > 65536:
        raise ValueError("exported best program escaped output or exceeded source cap")
    target = verified_dir / "best.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after opening, so a final symlink swap cannot redirect the read.
    fd = os.open(best, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("exported best program is not regular")
        source = os.read(fd, 65537)
        if len(source) > 65536:
            raise ValueError("exported best program exceeds source cap")
    finally:
        os.close(fd)
    target.write_bytes(source)
    return target


def _completion_status(evaluation_state: dict, verified: dict) -> str:
    statuses = [row["candidate_run"]["status"] for row in verified["families"]]
    return "COMPLETE" if evaluation_state["successes"] > 0 and all(s == "ok" for s in statuses) else "INCOMPLETE"


def _stage_inputs(args, run_dir: Path) -> tuple[Path, Path, Path | None, Path]:
    stage = run_dir / "stage"
    stage.mkdir()
    seed = stage / "initial_program.py"
    cases = stage / "cases.json"
    shutil.copyfile(args.seed, seed)
    shutil.copyfile(args.cases, cases)
    baseline = None
    if args.baseline:
        baseline = stage / "baseline.json"
        shutil.copyfile(args.baseline, baseline)
    # The evaluator and trusted core remain in the coordinator outside the
    # optimizer sandbox. Only this worker and public development inputs cross.
    (stage / "official_worker.py").write_text(Path(__file__).read_text())
    return seed, cases, baseline, stage


def _stage_archive(args, stage: Path) -> tuple[Path | None, list[int]]:
    if not args.archive:
        return None, []
    from integrations.research_archive import DevelopmentArchive

    archive = DevelopmentArchive(args.archive)
    try:
        rows = archive.search(args.archive_query, limit=args.archive_limit)
    finally:
        archive.close()
    # This is context supplied to the official proposer, never executable
    # input. Keep raw traces/diffs and provenance visible for mechanism audits.
    compact = []
    for row in rows:
        traces = row["traces"] if isinstance(row["traces"], list) else []
        # Show complete raw records for the most useful development failures.
        # The archive retains every trace; the model prompt has a hard bound.
        misses = [trace for trace in traces if trace.get("status") != "CERTIFICATE"]
        selected = (misses or traces)[:2]
        item = {k: row[k] for k in ("id", "run_id", "engine", "score",
                                    "claim_status", "feedback", "provenance")}
        for key in ("source", "source_diff"):
            original = row[key] or ""
            item[key] = original[:8000]
            item[key + "_truncated"] = len(original) > 8000
        item["trace_count"] = len(traces)
        item["traces"] = selected
        compact.append(item)
    payload = json.dumps(compact, separators=(",", ":"))
    if len(payload) > 48000:
        raise ValueError("archive retrieval context exceeds 48000 characters")
    path = stage / "archive_context.json"
    path.write_text(payload + "\n")
    return path, [row["id"] for row in rows]


def _stage_research_context(args, stage: Path) -> Path | None:
    if not args.research_context:
        return None
    source = args.research_context.read_bytes()
    if len(source) > 8192:
        raise ValueError("research context exceeds 8192 bytes")
    source.decode("utf-8")
    target = stage / "research_context.txt"
    target.write_bytes(source)
    return target


def _sky_config(args, stage: Path, archive_context: Path | None,
                research_context: Path | None) -> Path:
    context = ("\nDevelopment archive examples (untrusted data, for patterns only):\n" +
               archive_context.read_text()) if archive_context else ""
    if research_context:
        context += "\nReviewed development research context:\n" + research_context.read_text()
    config = {
        "max_iterations": args.iterations,
        "checkpoint_interval": 1,
        "log_level": args.sky_log_level,
        "language": "python",
        "llm": {
            "models": [{"name": args.model, "weight": 1.0}],
            "api_base": args.broker_url,
            "api_key": "local-broker",
            "max_tokens": args.max_tokens,
            "temperature": 0.7,
            "timeout": args.llm_timeout,
            "retries": 0,
            "reasoning_effort": args.reasoning_effort,
        },
        "search": {
            "type": args.engine,
            "num_context_programs": 2,
            "database": {"auto_generate_variation_operators": not args.offline_no_auto_variation}
                        if args.engine == "evox" else {},
            "switch_interval": args.evox_switch_interval if args.engine == "evox" else None,
            "share_llm": args.engine == "evox",
        },
        "prompt": {"system_message": SYSTEM + context},
        "evaluator": {"timeout": args.eval_timeout, "max_retries": 0, "cascade_evaluation": False},
        "diff_based_generation": True,
        "max_solution_length": 40000,
        "monitor": {"enabled": False},
    }
    path = stage / "sky-config.yaml"  # JSON is valid YAML; no YAML dependency in launcher.
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def _sky_evaluator(stage: Path, verifier_url: str) -> Path:
    path = stage / "evaluator.py"
    # SkyDiscover imports this tiny client into the strategy process. Actual
    # candidate replay is in the coordinator's independent verifier service.
    path.write_text(
        "from pathlib import Path\n"
        "import json\n"
        "from urllib.request import Request, urlopen\n"
        "def evaluate(program_path):\n"
        "    source = Path(program_path).read_text(encoding='utf-8')\n"
        "    payload = json.dumps({'source': source}).encode('utf-8')\n"
        f"    req = Request({verifier_url!r}, payload, {{'Content-Type': 'application/json'}})\n"
        "    with urlopen(req, timeout=120) as response:\n"
        "        return json.load(response)\n"
    )
    return path


def _verifier_service(cases: list[dict], baseline_path: Path | None,
                      run_dir: Path, max_requests: int, *, archive_path: Path | None,
                      engine: str, provenance: dict):
    from integrations.program_evaluator import ProgramEvaluator

    baseline = json.loads(baseline_path.read_text()) if baseline_path else None
    by_id = {case["id"]: case for case in cases}
    evidence = run_dir / "verified" / "evaluations"
    evidence.mkdir(parents=True)
    state = {"requests": 0, "successes": 0, "failures": 0}
    lock = threading.Lock()
    evaluation_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/evaluate":
                return self._reply(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 75000:
                return self._reply(413, {"error": "source request size exceeded"})
            with lock:
                if state["requests"] >= max_requests:
                    return self._reply(429, {"error": "evaluation request budget exhausted"})
                state["requests"] += 1
                ordinal = state["requests"]
            try:
                payload = json.loads(self.rfile.read(length))
                source = payload["source"]
                if not isinstance(source, str) or len(source.encode()) > 65536:
                    return self._reply(413, {"error": "candidate source size exceeded"})
                case_id = payload.get("case_id")
                if case_id is not None and case_id not in by_id:
                    return self._reply(400, {"error": "unknown development case"})
                selected = [by_id[case_id]] if case_id else cases
                candidate = evidence / f"candidate-{ordinal:04d}.py"
                candidate.write_text(source)
                with evaluation_lock:
                    result = ProgramEvaluator(selected, baseline=baseline,
                                              require_os_sandbox=True).evaluate(candidate)
                    if archive_path:
                        from integrations.research_archive import DevelopmentArchive
                        archive = DevelopmentArchive(archive_path)
                        try:
                            statuses = [row["candidate_run"]["status"] for row in result["families"]]
                            archive.add(run_id=run_dir.name, engine=engine, source=source,
                                        score=result["combined_score"],
                                        feedback={"summary": result["feedback"],
                                                  "certified": result["certified"],
                                                  "new_certified": result["new_certified"]},
                                        traces=result["families"], provenance=provenance,
                                        claim_status=("finite_development" if all(s == "ok" for s in statuses)
                                                      else "incomplete"))
                        finally:
                            archive.close()
                artifact = evidence / f"result-{ordinal:04d}.json"
                artifact.write_text(json.dumps(result, indent=2, default=str) + "\n")
                runs = [row["candidate_run"]["status"] for row in result["families"]]
                with lock:
                    state["successes"] += sum(status == "ok" for status in runs)
                    state["failures"] += sum(status != "ok" for status in runs)
                traces = [{"case_id": row["case"]["id"],
                           "status": row["status"],
                           "candidate_run": row["candidate_run"],
                           "accepted_words": [{"word": item.get("normalized_word", item.get("raw_word")),
                                               "base": item["profile"]["base"],
                                               "gamma": item["profile"]["gamma"]}
                                              for item in row["accepted_words"][:3]],
                           "rejected_words": row["rejected_words"][:4],
                           "lp_status": row["lp"]["status"],
                           "baseline_lp_status": row["baseline_lp"]["status"]}
                          for row in result["families"]]
                summary = {"combined_score": result["combined_score"],
                           "artifacts": {"feedback": result["feedback"],
                                         "case_statuses": runs,
                                         "traces": traces,
                                         "evaluation": str(artifact)},
                           "certified": result["certified"],
                           "new_certified": result["new_certified"],
                           "candidate_hash": result["candidate_hash"]}
                return self._reply(200, summary)
            except Exception as exc:
                with lock:
                    state["failures"] += 1
                return self._reply(500, {"error": f"trusted evaluation failed: {type(exc).__name__}: {exc}"})

        def _reply(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, state, f"http://127.0.0.1:{server.server_port}/evaluate"


def _worker_environment(stage: Path, run_dir: Path, broker_url: str) -> dict[str, str]:
    # No provider credential reaches generated solution or EvoX strategy code.
    # Keep only interpreter/runtime essentials and force the SDK to local HTTP.
    keep = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "DYLD_LIBRARY_PATH")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update({
        "HOME": str(run_dir / "output"),
        "TMPDIR": str(run_dir / "output" / "tmp"),
        "PYTHONPATH": str(stage),
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENAI_API_KEY": "local-broker",
        "OPENAI_API_BASE": broker_url,
        "OPENAI_BASE_URL": broker_url,
    })
    return env


def _launch(args) -> dict:
    from integrations.program_sandbox import sandbox_command, sandbox_profile

    if args.engine not in UPSTREAM:
        raise ValueError(args.engine)
    if args.iterations < 1 or args.max_tokens < 1:
        raise ValueError("iterations and max_tokens must be positive")
    args.broker_url = _broker_url(args.broker_url)
    input_provenance = _verify_inputs(args)
    _load_cases(args.cases)
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        raise FileExistsError(run_dir)
    run_dir.mkdir(parents=True)
    (run_dir / "output" / "tmp").mkdir(parents=True)
    seed, cases, baseline, stage = _stage_inputs(args, run_dir)
    archive_context, archive_ids = _stage_archive(args, stage)
    research_context = _stage_research_context(args, stage)
    python = args.python.absolute()
    if not python.is_file():
        raise FileNotFoundError(python)
    upstream_identity = _installed_identity(python, args.engine)
    server, eval_state, verifier_url = _verifier_service(
        _load_cases(cases), baseline, run_dir, args.max_evals,
        archive_path=args.archive, engine=args.engine,
        provenance={"upstream": upstream_identity, "seed_sha256": _source_digest(seed),
                    "cases_sha256": _source_digest(cases), **input_provenance})
    env = _worker_environment(stage, run_dir, args.broker_url)
    if args.engine == "gepa":
        command = [str(python), str(stage / "official_worker.py"), "_gepa_worker",
                   "--seed", str(seed), "--cases", str(cases), "--run-dir", str(run_dir / "output"),
                   "--broker-url", args.broker_url, "--model", args.model,
                   "--verifier-url", verifier_url,
                   "--max-tokens", str(args.max_tokens), "--proposals", str(args.iterations),
                   "--llm-timeout", str(args.llm_timeout)]
        if args.reasoning_effort:
            command += ["--reasoning-effort", args.reasoning_effort]
        if baseline:
            command += ["--baseline", str(baseline)]
        if args.offline_proposal:
            shutil.copyfile(args.offline_proposal, stage / "offline_proposal.py")
            command += ["--offline-proposal", str(stage / "offline_proposal.py")]
        if archive_context:
            command += ["--archive-context", str(archive_context)]
        if research_context:
            command += ["--research-context", str(research_context)]
    else:
        config = _sky_config(args, stage, archive_context, research_context)
        evaluator = _sky_evaluator(stage, verifier_url)
        command = [str(python), "-m", "skydiscover", "optimize", str(seed), str(evaluator),
                   "--config", str(config), "--search", args.engine,
                   "--iterations", str(args.iterations), "--output", str(run_dir / "output" / "sky"),
                   "--log-level", args.sky_log_level]
    # The official worker may read only staged development inputs, system
    # runtime and installed packages. All writes go to this run's directory.
    base_python = Path(os.path.realpath(python))
    read_paths = ["/System", "/usr", "/Library", "/opt/homebrew", "/private/etc", "/dev",
                  str(python.parent.parent), str(base_python.parent.parent), str(stage)]
    profile = run_dir / "worker.sb"
    port = urlparse(args.broker_url).port
    if port is None:
        raise ValueError("broker URL needs an explicit port")
    profile.write_text(sandbox_profile(read_paths=read_paths,
                                      write_paths=[run_dir / "output"],
                                      loopback_ports=[port, urlparse(verifier_url).port],
                                      allow_python_multiprocessing=True))
    wrapped = sandbox_command(command, profile)
    manifest = {
        "engine": args.engine, "upstream": upstream_identity,
        **input_provenance,
        "seed_sha256": _source_digest(seed), "cases_sha256": _source_digest(cases),
        "baseline_sha256": _source_digest(baseline) if baseline else None,
        "broker_url": args.broker_url, "model": args.model,
        "iterations": args.iterations, "max_tokens": args.max_tokens,
        "wall_seconds": args.wall_seconds,
        "archive_ids": archive_ids,
        "archive_context_sha256": _source_digest(archive_context) if archive_context else None,
        "research_context_sha256": _source_digest(research_context) if research_context else None,
        "verifier_url": verifier_url, "max_evals": args.max_evals,
        "command": command, "sandbox_command": wrapped,
        "sandbox_profile": str(profile), "run_dir": str(run_dir),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        with (run_dir / "console.log").open("w") as log:
            proc = subprocess.Popen(wrapped, cwd=run_dir / "output", env=env, stdout=log,
                                    stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                returncode = proc.wait(timeout=args.wall_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                returncode = proc.returncode
                manifest["status"] = "INCOMPLETE"
                manifest["reason"] = "official optimizer wall time limit"
            finally:
                # Reap any detached descendants before inspecting exported
                # source, even if the direct optimizer process exited cleanly.
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    finally:
        server.shutdown()
        server.server_close()
    manifest["candidate_evaluations"] = eval_state.copy()
    manifest["returncode"] = returncode
    if returncode and "status" not in manifest:
        manifest["status"] = "INCOMPLETE"
        manifest["reason"] = "official optimizer exited nonzero"
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if returncode:
        raise RuntimeError(f"official {args.engine} exited {returncode}; see {run_dir / 'console.log'}")
    # The upstream engine (especially EvoX) may have changed its own process
    # state. Re-score the exported source in this separate trusted coordinator.
    from integrations.program_evaluator import evaluate as trusted_evaluate
    best = (run_dir / "output" / "best.py" if args.engine == "gepa" else
            run_dir / "output" / "sky" / "best" / "best_program.py")
    trusted_best = _snapshot_best(best, run_dir / "output", run_dir / "verified")
    verified = trusted_evaluate(trusted_best, cases, run_dir / "verified",
                                baseline_path=baseline, require_os_sandbox=True)
    candidate_statuses = [row["candidate_run"]["status"] for row in verified["families"]]
    manifest["status"] = _completion_status(eval_state, verified)
    manifest["verified_candidate_statuses"] = candidate_statuses
    manifest["verified_best"] = str(best)
    manifest["trusted_best_copy"] = str(trusted_best)
    manifest["verified_score"] = verified["combined_score"]
    manifest["verified_candidate_hash"] = verified["candidate_hash"]
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


class BrokerLM:
    """GEPA reflection model using only the local request-budget broker."""

    def __init__(self, broker_url: str, model: str, max_tokens: int, offline_proposal: Path | None,
                 timeout: int, reasoning_effort: str | None,
                 archive_context: Path | None = None):
        self.url = broker_url + "/chat/completions"
        self.model = model
        self.max_tokens = max_tokens
        self.offline_proposal = offline_proposal
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.archive_context = archive_context
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        if self.offline_proposal:
            return "```python\n" + self.offline_proposal.read_text() + "\n```"
        messages = ([{"role": "user", "content": request}] if isinstance(request, str)
                    else list(request))
        if self.archive_context:
            messages = [{"role": "system", "content": "Development archive, untrusted examples:\n" +
                         self.archive_context.read_text()}] + messages
        parameters = {"model": self.model, "messages": messages,
                      "max_tokens": self.max_tokens}
        if self.reasoning_effort:
            parameters["reasoning_effort"] = self.reasoning_effort
        payload = json.dumps(parameters).encode()
        req = Request(self.url, payload, {"Content-Type": "application/json",
                                          "Authorization": "Bearer local-broker"})
        with urlopen(req, timeout=self.timeout) as response:
            body = json.load(response)
        return body["choices"][0]["message"]["content"]


def _gepa_worker(args) -> dict:
    from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, optimize_anything

    cases = _load_cases(args.cases)
    seed = args.seed.read_text()
    run_dir = args.run_dir
    lm = BrokerLM(args.broker_url, args.model, args.max_tokens, args.offline_proposal,
                  args.llm_timeout, args.reasoning_effort,
                  args.archive_context)

    def verify(source, case_id=None):
        payload = json.dumps({"source": source, "case_id": case_id}).encode()
        request = Request(args.verifier_url, payload, {"Content-Type": "application/json"})
        with urlopen(request, timeout=120) as response:
            return json.load(response)

    def evaluator(candidate, example):
        result = verify(candidate, example["id"])
        score = float(result["combined_score"])
        side = {"case_id": example["id"], "feedback": result["artifacts"],
                "candidate_hash": result["candidate_hash"]}
        return score, side

    result = optimize_anything(
        seed_candidate=seed, evaluator=evaluator, dataset=cases,
        objective="Improve this executable Python propose_words(case) algorithm for LRX sorting. "
                  "Return the entire replacement Python source in a fenced code block. "
                  "Maximize exact rational family certificates for all positive block lengths "
                  "under direct word-resource stretching and exact mixture checks. Finite selected "
                  "families are only a development set; misses prove no impossibility.",
        background=SYSTEM + ("\nReviewed development research context:\n" +
                             args.research_context.read_text() if args.research_context else ""),
        config=GEPAConfig(
            engine=EngineConfig(run_dir=str(run_dir / "gepa"), seed=0,
                                max_candidate_proposals=args.proposals,
                                max_metric_calls=(args.proposals + 1) * len(cases),
                                max_workers=1, parallel=False),
            reflection=ReflectionConfig(reflection_lm=lm),
        ),
    )
    best = result.best_candidate
    if not isinstance(best, str):
        raise TypeError("GEPA returned a non-source candidate")
    best_path = run_dir / "best.py"
    best_path.write_text(best)
    full = verify(best)
    summary = {"engine": "gepa", "upstream": UPSTREAM["gepa"],
               "best_path": str(best_path), "best_score": full["combined_score"],
               "reflection_calls": lm.calls, "full_evaluation": full}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--engine", required=True, choices=tuple(UPSTREAM))
    run.add_argument("--seed", required=True, type=Path)
    run.add_argument("--cases", required=True, type=Path)
    run.add_argument("--baseline", type=Path)
    run.add_argument("--frozen-manifest", type=Path)
    run.add_argument("--allow-custom-cases", action="store_true")
    run.add_argument("--run-dir", required=True, type=Path)
    run.add_argument("--python", type=Path, default=ROOT / ".venv-official/bin/python")
    run.add_argument("--broker-url", required=True)
    run.add_argument("--model", default="grok-4.7")
    run.add_argument("--iterations", type=int, default=10)
    run.add_argument("--max-tokens", type=int, default=4000)
    run.add_argument("--eval-timeout", type=int, default=120)
    run.add_argument("--llm-timeout", type=int, default=120)
    run.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"),
                     help="Grok reasoning effort; omit to use upstream default")
    run.add_argument("--wall-seconds", type=int, default=600)
    run.add_argument("--max-evals", type=int, default=256)
    run.add_argument("--evox-switch-interval", type=int, default=2)
    run.add_argument("--sky-log-level", choices=("DEBUG", "INFO", "WARNING"), default="INFO")
    run.add_argument("--offline-no-auto-variation", action="store_true",
                     help="offline mock only: use upstream fixed variation templates")
    run.add_argument("--offline-proposal", type=Path,
                     help="GEPA-only local reflection fixture; no model request")
    run.add_argument("--archive", type=Path, help="development-only SQLite retrieval archive")
    run.add_argument("--archive-query", default="")
    run.add_argument("--archive-limit", type=int, default=2)
    run.add_argument("--research-context", type=Path,
                     help="reviewed development-only prompt context, capped at 8192 bytes")
    worker = sub.add_parser("_gepa_worker")
    for flag in ("seed", "cases", "run-dir", "broker-url", "verifier-url", "model", "max-tokens", "proposals", "llm-timeout"):
        worker.add_argument("--" + flag, required=True,
                            type=Path if flag in ("seed", "cases", "run-dir") else int if flag in ("max-tokens", "proposals", "llm-timeout") else str)
    worker.add_argument("--baseline", type=Path)
    worker.add_argument("--offline-proposal", type=Path)
    worker.add_argument("--archive-context", type=Path)
    worker.add_argument("--research-context", type=Path)
    worker.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"))
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    result = _launch(args) if args.action == "run" else _gepa_worker(args)
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
