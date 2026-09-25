"""Sandboxed subprocess runner for the Lean evaluator stages (no network, timeout, rlimits).

Local Seatbelt variant of program_sandbox.sandbox_profile (that file is not
changed): deny by default, no network or loopback, no mach-lookup, and no
`(allow process*)`. A stage may exec only the listed trusted binaries; fork is
granted only when a stage needs it (leanchecker runs `lean --print-prefix`).
Reads are limited to the toolchain, the locked build directory, system
libraries and the listed scratch directories; writes to one scratch directory.
Stdout/stderr go to parent-owned files outside every sandbox path.
"""
from __future__ import annotations

import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from integrations.program_sandbox import SandboxUnavailable

SYSTEM_READS = ("/usr/lib", "/System", "/private/etc", "/private/var/db/dyld", "/Library/Apple")
MAX_CAPTURE = 1 << 20


def _q(path) -> str:
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _ancestors(paths):
    seen = []
    for p in paths:
        p = os.path.dirname(os.path.realpath(p))
        while p not in ("/", "") and p not in seen:
            seen.append(p)
            p = os.path.dirname(p)
    return seen


def lean_profile(*, exec_paths, read_paths=(), write_paths=(), allow_fork=False) -> str:
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        raise SandboxUnavailable("macOS sandbox-exec is unavailable")
    reads = [os.path.realpath(p) for p in read_paths]
    writes = [os.path.realpath(p) for p in write_paths]
    execs = [os.path.realpath(p) for p in exec_paths]
    lines = ["(version 1)", "(deny default)", "(allow sysctl-read)",
             '(allow file-read* (literal "/"))',
             '(allow file-read* (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))',
             '(allow file-write* (literal "/dev/null"))']
    lines += [f"(allow process-exec (literal {_q(p)}))" for p in execs]
    if allow_fork:
        lines.append("(allow process-fork)")
    lines += [f"(allow file-read* (subpath {_q(p)}))" for p in (*SYSTEM_READS, *reads, *execs)]
    lines += [f"(allow file-read* file-write* (subpath {_q(p)}))" for p in writes]
    # Lean resolves its own executable path; grant metadata (not contents) of ancestors only.
    lines += [f"(allow file-read-metadata (literal {_q(p)}))" for p in _ancestors([*reads, *writes, *execs])]
    return "\n".join(lines) + "\n"


def _limits(cpu, fsize, nofile):
    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        want = nofile if hard == resource.RLIM_INFINITY else min(nofile, hard)
        resource.setrlimit(resource.RLIMIT_NOFILE, (want, hard))
    return apply


def _rss_mb(pid) -> float:
    try:
        out = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return int(out.stdout.split()[0]) / 1024 if out.stdout.split() else 0.0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def run(command, *, cwd, env, profile_text=None, wall=60.0, fsize=64 << 20, nofile=4096,
        rss_limit_mb=4096, require_sandbox=True) -> dict:
    """Run one stage. Timeout or memory kill gives status INCOMPLETE, never a verdict."""
    with tempfile.TemporaryDirectory(prefix="lrx-lean-io-") as io:
        io = Path(io)
        wrapped = list(map(str, command))
        if profile_text is not None:
            (io / "stage.sb").write_text(profile_text)
            wrapped = [shutil.which("sandbox-exec"), "-f", str(io / "stage.sb"), *wrapped]
        elif require_sandbox:
            raise SandboxUnavailable("a sandbox profile is required for Lean stages")
        start = time.monotonic()
        status, reason = "ok", None
        with open(io / "out", "wb") as out, open(io / "err", "wb") as err:
            proc = subprocess.Popen(wrapped, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                    start_new_session=True,
                                    preexec_fn=_limits(int(wall) + 1, fsize, nofile))
            try:
                last_rss = 0.0
                while proc.poll() is None:
                    elapsed = time.monotonic() - start
                    if elapsed > wall:
                        status, reason = "INCOMPLETE", f"wall time limit {wall:g} s"
                        break
                    if elapsed - last_rss >= 1.0:
                        last_rss = elapsed
                        if _rss_mb(proc.pid) > rss_limit_mb:
                            status, reason = "INCOMPLETE", f"memory limit {rss_limit_mb} MB"
                            break
                    time.sleep(0.05)
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                proc.wait()
        rc = proc.returncode
        if status == "ok" and rc is not None and rc < 0 and -rc in (signal.SIGXCPU, signal.SIGKILL):
            status, reason = "INCOMPLETE", f"killed by signal {-rc}"
        return {"status": status, "reason": reason, "returncode": rc,
                "seconds": round(time.monotonic() - start, 3),
                "stdout": (io / "out").read_bytes()[:MAX_CAPTURE].decode("utf-8", "replace"),
                "stderr": (io / "err").read_bytes()[:MAX_CAPTURE].decode("utf-8", "replace")}
