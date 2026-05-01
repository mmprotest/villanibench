from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    wall_time_sec: float


def _subprocess_text_kwargs() -> dict[str, str | bool]:
    """Use deterministic subprocess text decoding across platforms.

    Windows defaults to the active console code page, often cp1252. Runner
    CLIs may emit UTF-8, ANSI escape sequences, box drawing characters, model
    output, or other bytes that are not valid in that code page. Without an
    explicit encoding, subprocess reader threads can raise UnicodeDecodeError
    and make a successful runner look like it crashed.
    """
    return {
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }


def run_command_tree(command: str, cwd: Path, timeout_sec: float, env: dict[str, str] | None = None) -> ProcessResult:
    start = time.monotonic()
    kwargs = dict(cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **_subprocess_text_kwargs())
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout_sec)
        return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic() - start)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
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
        return ProcessResult(124, out or "", err, True, time.monotonic() - start)


def run_command_tree_argv(
    argv: list[str],
    cwd: Path,
    timeout_sec: float,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> ProcessResult:
    start = time.monotonic()
    kwargs = dict(cwd=cwd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **_subprocess_text_kwargs())
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(argv, **kwargs)
    try:
        out, err = proc.communicate(input=stdin_text, timeout=timeout_sec)
        return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic() - start)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
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
        return ProcessResult(124, out or "", err, True, time.monotonic() - start)