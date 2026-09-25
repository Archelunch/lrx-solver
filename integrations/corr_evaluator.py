"""Trusted evaluator for corr-cert candidates (autoresearch/corr-cert-260924/TASK.md).

A candidate program exposes `coefficients(m) -> dict` returning the JSON-safe
encoding of a Theorem-3 certificate (see integrations/corr_task.py). It runs
only in a separate process under the official-integration Seatbelt profile
(program_sandbox.py, program_evaluator._preexec, unchanged, exactly as
lift_evaluator.py uses them). Only the JSON-safe dict crosses back; the
trusted parent here decodes it, calls corrcert.check_certificate exactly, and
computes the score. A miss, crash or time limit is never evidence that no
certificate exists for that m.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as Fr
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations.corr_task import _CORRCERT_PATH, canonical, corrcert, decode_cert
from integrations.program_evaluator import MAX_OUTPUT_BYTES, _preexec
from integrations.program_sandbox import SandboxUnavailable, sandbox_command, sandbox_profile

VERSION = "corr-eval-1"
CONTRACT = (
    "corr-contract-1: candidate defines coefficients(m) -> JSON-safe cert dict (see "
    "integrations/corr_task.py encode_cert/decode_cert for the exact key encoding). "
    "For each m, decode and call corrcert.check_certificate(m, cert); pass iff ok==True "
    "and epsilon < 1. violation magnitude for a failing m = sum(-slack) over every violated "
    "(5)/(6) check plus max(0, epsilon-1); an invalid/crash/timeout output contributes the "
    "fixed penalty INVALID_GAP instead (never repaired, never partial credit). "
    "combined_score = passes + 0.5/(1+violation_sum), violation_sum summed over m that did "
    "not pass. Stdlib only, source <= 64 KiB, wall limit 10s per m."
)
INVALID_GAP = 5000  # fixed penalty for crash/timeout/invalid-output per m; see TASK.md
MAX_SOURCE = 65536
TIMEOUT_PER_M = 10.0
MAX_VIOLATIONS = 1_000_000  # effectively "all" for m <= 20 (expected_checks(20) ~ 1.4M)
_SOURCES = ("corr_evaluator.py", "corr_task.py", "corr_worker.py", "program_sandbox.py")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evaluator_hash() -> str:
    here = Path(__file__).parent
    return _sha(VERSION.encode() + b"".join((here / f).read_bytes() for f in _SOURCES)
                + _CORRCERT_PATH.read_bytes())


# ------------------------------------------------------------- sandbox run
def run_program(source: bytes, m: int, timeout: float, require_os_sandbox=True) -> dict:
    """Same mechanism as lift_evaluator.run_program, with corr_worker.py and a {"m": m} case."""
    with tempfile.TemporaryDirectory(prefix="lrx-corr-") as temp:
        scratch = Path(temp).resolve()
        (scratch / "candidate.py").write_bytes(source)
        shutil.copyfile(Path(__file__).with_name("corr_worker.py"), scratch / "worker.py")
        (scratch / "case.json").write_text(json.dumps({"m": m}))
        out = scratch / "output.json"
        command = [sys.executable, "-I", "-S", str(scratch / "worker.py"), str(scratch / "candidate.py"),
                   str(scratch / "case.json"), str(out)]
        isolation = "process_only"
        if require_os_sandbox:
            profile = sandbox_profile(read_paths=(sys.base_prefix, "/usr", "/System", "/Library", "/private/etc"),
                                      write_paths=(scratch,))
            (scratch / "sandbox.sb").write_text(profile, encoding="utf-8")
            command = sandbox_command(command, scratch / "sandbox.sb")
            isolation = "macos_seatbelt"
        env = {"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch),
               "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C"}
        start = time.monotonic()
        with (scratch / "stdout").open("wb") as so, (scratch / "stderr").open("wb") as se:
            proc = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=so,
                                    stderr=se, start_new_session=True, preexec_fn=lambda: _preexec(timeout))
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                return {"status": "INCOMPLETE", "reason": "time limit", "seconds": time.monotonic() - start,
                        "isolation": isolation}
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        meta = {"seconds": time.monotonic() - start, "isolation": isolation}
        log = (scratch / "stderr").read_bytes()[:4096].decode("utf-8", "replace")
        if proc.returncode:
            if "sandbox_apply: Operation not permitted" in log:
                raise SandboxUnavailable("macOS Seatbelt denied by outer execution environment")
            return dict(meta, status="INCOMPLETE", reason="worker exit %d" % proc.returncode, stderr=log)
        if not out.exists() or out.stat().st_size > MAX_OUTPUT_BYTES:
            return dict(meta, status="INCOMPLETE", reason="missing or oversized worker output")
        try:
            payload = json.loads(out.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            return dict(meta, status="INCOMPLETE", reason="invalid worker JSON")
        if not isinstance(payload, dict) or payload.get("status") not in ("ok", "candidate_error"):
            return dict(meta, status="INVALID_OUTPUT", reason="worker JSON must be a status object")
        return dict(payload, **meta)


# ------------------------------------------------------------- scoring
def score_m(m: int, attempt: dict) -> dict:
    row = {"m": m, "passed": False, "epsilon": None, "magnitude": INVALID_GAP,
           "run": {x: attempt.get(x) for x in ("seconds", "isolation", "reason", "error") if x in attempt},
           "violations": []}
    if attempt["status"] != "ok":
        row["status"] = attempt["status"]
        row["failure"] = attempt.get("reason") or attempt.get("error")
        return row
    try:
        cert = decode_cert(m, attempt.get("output"))
    except (ValueError, KeyError, TypeError) as exc:
        row["status"] = "INVALID_OUTPUT"
        row["failure"] = str(exc)[:300]
        return row
    res = corrcert.check_certificate(m, cert, max_violations=MAX_VIOLATIONS)
    if res["violations"] and res["violations"][0][0] == "malformed":
        row["status"] = "INVALID_OUTPUT"
        row["failure"] = "malformed certificate: %s" % (res["violations"][0][1],)
        return row
    eps = res["epsilon"]
    row["epsilon"] = str(eps)
    row["checks"] = res["checks"]
    row["n_violations"] = res["n_violations"]
    magnitude = sum(-entry[-1] for entry in res["violations"])  # slack < 0 for a violation
    if eps is not None and eps > 1:
        magnitude += eps - 1
    row["violations"] = [list(v) for v in
                          sorted(res["violations"], key=lambda v: v[-1])[:3]]  # 3 worst (most negative slack)
    if res["proves"]:
        row["status"], row["passed"], row["magnitude"] = "PASS", True, "0"
        return row
    row["status"] = "FAIL"
    row["magnitude"] = str(magnitude)
    return row


def load_instances(path) -> list[int]:
    from integrations.corr_task import guard_not_holdout, load_m_set

    p = Path(path)
    guard_not_holdout(p)
    return load_m_set(p)


def evaluate(program_path, m_values, *, timeout=TIMEOUT_PER_M, require_os_sandbox=True, jobs=4, cache_dir=None):
    src = Path(program_path)
    if src.is_symlink() or not src.is_file() or src.stat().st_size > MAX_SOURCE:
        raise ValueError("candidate must be a regular file of at most %d bytes" % MAX_SOURCE)
    source = src.read_bytes()
    m_values = sorted(set(int(m) for m in m_values))
    set_hash = _sha(canonical(m_values).encode())
    key = _sha(canonical([_sha(source), set_hash, evaluator_hash(), CONTRACT, require_os_sandbox]).encode())
    cache = Path(cache_dir) / (key + ".json") if cache_dir else None
    if cache and cache.exists():
        return dict(json.loads(cache.read_text()), cache_hit=True)
    start = time.monotonic()
    with ThreadPoolExecutor(max(1, jobs)) as pool:
        attempts = list(pool.map(lambda m: run_program(source, m, timeout, require_os_sandbox), m_values))
    rows = [score_m(m, a) for m, a in zip(m_values, attempts)]
    passes = sum(r["passed"] for r in rows)
    violation_sum = sum(Fr(r["magnitude"]) for r in rows if not r["passed"])
    result = {"kind": "corr_cert_program", "evaluator_version": VERSION, "evaluator_hash": evaluator_hash(),
              "contract": CONTRACT, "cache_key": key, "candidate_hash": _sha(source),
              "m_set_hash": set_hash, "m_values": m_values, "passes": passes,
              "violation_sum": str(violation_sum), "invalid": sum(r["status"] not in ("PASS", "FAIL") for r in rows),
              "timeouts": sum(r["run"].get("reason") == "time limit" for r in rows),
              "combined_score": passes + 0.5 / (1 + float(violation_sum)),
              "isolation": "macos_seatbelt" if require_os_sandbox else "process_only",
              "seconds": time.monotonic() - start, "results": rows,
              "limitations": ["Finite frozen development m-set only. Word replay / LP verification never "
                              "extends beyond the m values evaluated; a miss or timeout proves nothing about "
                              "any m, and passing every development m is not a proof for general m."]}
    if cache and not any(r["status"] == "INCOMPLETE" for r in rows):
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result))
    return dict(result, cache_hit=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", required=True)
    ap.add_argument("--m-set", required=True, help="frozen m-set JSON (development.json)")
    ap.add_argument("--output", required=True)
    ap.add_argument("--timeout", type=float, default=TIMEOUT_PER_M)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cache-dir")
    ap.add_argument("--no-os-sandbox", action="store_true", help="trusted controls only; never generated code")
    a = ap.parse_args(argv)
    m_values = load_instances(a.m_set)
    res = evaluate(a.program, m_values, timeout=a.timeout, require_os_sandbox=not a.no_os_sandbox,
                   jobs=a.jobs, cache_dir=a.cache_dir)
    out = Path(a.output)
    if out.exists():
        raise SystemExit("refusing to overwrite existing %s" % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({x: res[x] for x in ("passes", "violation_sum", "invalid", "timeouts",
                                          "combined_score", "isolation", "seconds", "cache_hit")}))


if __name__ == "__main__":
    main()
