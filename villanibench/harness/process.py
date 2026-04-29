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


def run_command_tree(command: str, cwd: Path, timeout_sec: float, env: dict[str, str] | None = None) -> ProcessResult:
    start = time.monotonic()
    kwargs = dict(cwd=cwd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout_sec)
        return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic()-start)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
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
        out, err = proc.communicate()
        msg = f"Command timed out after {timeout_sec:.1f}s and was terminated."
        err = f"{(err or '').rstrip()}\n{msg}".strip()
        return ProcessResult(124, out or "", err, True, time.monotonic()-start)
