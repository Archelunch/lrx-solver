"""Small Seatbelt wrapper for explicitly authorized generated Python programs.

The profile is deliberately a filesystem allowlist.  A caller must launch the
wrapped command in an environment that permits nested macOS sandboxing.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys


class SandboxUnavailable(RuntimeError):
    pass


def _literal(path: os.PathLike[str] | str) -> str:
    value = str(Path(path).resolve())
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def sandbox_profile(*, read_paths=(), write_paths=(), loopback_ports=(),
                    allow_python_multiprocessing=False) -> str:
    """Return a deny-by-default macOS sandbox profile for a separate process.

    `read_paths` and `write_paths` must be absolute, caller-owned allowlists.
    The OS mediates descendants as well as the initial process.  This is a
    macOS Seatbelt profile, not a portable container policy.
    """
    if sys.platform != 'darwin' or not shutil.which('sandbox-exec'):
        raise SandboxUnavailable('macOS sandbox-exec is unavailable')
    lines = ['(version 1)', '(deny default)', '(allow process*)',
             '(allow sysctl-read)', '(allow mach-lookup)',
             # Dyld/Python inspect the root directory during startup.  This
             # grants that directory entry only, not descendants.
             '(allow file-read* (literal "/"))',
             '(allow file-read* (literal "/dev/null"))',
             '(allow file-write* (literal "/dev/null"))']
    for path in read_paths:
        lines.append(f'(allow file-read* (subpath {_literal(path)}))')
    for path in write_paths:
        quoted = _literal(path)
        lines.append(f'(allow file-read* (subpath {quoted}))')
        lines.append(f'(allow file-write* (subpath {quoted}))')
    for port in loopback_ports:
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('loopback port must be 1..65535')
        lines.append(f'(allow network* (remote ip "localhost:{port}"))')
    if allow_python_multiprocessing:
        # multiprocessing.Event/Lock uses Python-owned POSIX semaphore names
        # on macOS.  Generated candidate workers do not receive this grant.
        lines.append('(allow ipc-posix-sem (ipc-posix-name-regex #"^/mp-"))')
    return '\n'.join(lines) + '\n'


def sandbox_command(command, profile_path):
    """Wrap a command in a previously written profile; never silently fall back."""
    if sys.platform != 'darwin' or not shutil.which('sandbox-exec'):
        raise SandboxUnavailable('macOS sandbox-exec is unavailable')
    return [shutil.which('sandbox-exec'), '-f', str(profile_path), *map(str, command)]
