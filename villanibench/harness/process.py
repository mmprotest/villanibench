from __future__ import annotations

import os
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from villanibench.harness.os_sandbox_user import SandboxIdentity


@dataclass
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    wall_time_sec: float


def _subprocess_text_kwargs() -> dict[str, str | bool]:
    return {"text": True, "encoding": "utf-8", "errors": "replace"}


def _popen_kwargs(cwd: Path, env: dict[str, str] | None) -> dict:
    kwargs = dict(cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **_subprocess_text_kwargs())
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _timeout_cleanup(proc: subprocess.Popen, timeout_sec: float) -> tuple[str, str, str]:
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, **_subprocess_text_kwargs())
        except Exception:
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            proc.wait(timeout=0.5)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
    cleanup_msg = ""
    try:
        out, err = proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        cleanup_msg = " Process did not terminate cleanly after timeout."
        try:
            proc.kill()
        except Exception:
            pass
        try:
            out, err = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            out, err = "", "Process did not terminate cleanly after timeout."
    msg = f"Command timed out after {timeout_sec:.1f}s and was terminated.{cleanup_msg}"
    err = f"{(err or '').rstrip()}\n{msg}".strip()
    return out or "", err, msg


def _linux_prefix(identity: SandboxIdentity) -> list[str]:
    if os.geteuid() != 0:
        raise RuntimeError("Launching sandboxed subprocesses on Linux requires root/admin privileges.")
    return ["runuser", "-u", identity.username, "--"]


def run_command_tree(command: str, cwd: Path, timeout_sec: float, env: dict[str, str] | None = None, sandbox_identity: SandboxIdentity | None = None) -> ProcessResult:
    start = time.monotonic()
    kwargs = _popen_kwargs(cwd, env)
    if sandbox_identity is None:
        proc = subprocess.Popen(command, shell=True, **kwargs)
    else:
        if os.name == "nt":
            raise RuntimeError("Windows sandboxed subprocess launch is not implemented.")
        if os.name == "posix" and os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandboxed subprocess launch is not implemented.")
        argv = _linux_prefix(sandbox_identity) + ["bash", "-lc", command]
        proc = subprocess.Popen(argv, shell=False, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout_sec)
        return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic() - start)
    except subprocess.TimeoutExpired:
        out, err, _ = _timeout_cleanup(proc, timeout_sec)
        return ProcessResult(124, out, err, True, time.monotonic() - start)


def run_command_tree_argv(
    argv: list[str],
    cwd: Path,
    timeout_sec: float,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
    sandbox_identity: SandboxIdentity | None = None,
) -> ProcessResult:
    start = time.monotonic()
    kwargs = _popen_kwargs(cwd, env)
    cmd_argv = argv
    if sandbox_identity is not None:
        if os.name == "nt":
            raise RuntimeError("Windows sandboxed subprocess launch is not implemented.")
        if os.name == "posix" and os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandboxed subprocess launch is not implemented.")
        cmd_argv = _linux_prefix(sandbox_identity) + argv
    proc = subprocess.Popen(cmd_argv, shell=False, **kwargs)
    try:
        out, err = proc.communicate(input=stdin_text, timeout=timeout_sec)
        return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic() - start)
    except subprocess.TimeoutExpired:
        out, err, _ = _timeout_cleanup(proc, timeout_sec)
        return ProcessResult(124, out, err, True, time.monotonic() - start)
