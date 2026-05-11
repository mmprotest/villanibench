from __future__ import annotations

import ctypes
import os
import secrets
import shutil
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path

SANDBOX_USERNAME = "villanibench_sandbox"


@dataclass
class SandboxIdentity:
    username: str
    password: str | None
    created: bool = True


def _generate_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + "_.-"
    return "".join(secrets.choice(alphabet) for _ in range(length))




def _run_admin_command(
    argv: list[str], *, timeout_sec: float = 20.0, allow_failure: bool = False, display_argv: list[str] | None = None
) -> subprocess.CompletedProcess:
    shown = display_argv or argv
    shown_cmd = " ".join(shown)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command '{shown[0]}' timed out after {timeout_sec:.1f}s.") from exc
    if not allow_failure and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"Command failed ({shown_cmd}): {detail}")
    return proc


def _is_windows_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def create_sandbox_identity() -> SandboxIdentity:
    password = _generate_password()
    if os.name == "nt":
        if not _is_windows_admin():
            raise RuntimeError("Creating sandbox user 'villanibench_sandbox' requires an elevated Administrator shell on Windows.")
        _run_admin_command(["net", "user", SANDBOX_USERNAME, "/delete"], allow_failure=True)
        _run_admin_command(
            ["net", "user", SANDBOX_USERNAME, password, "/add"],
            display_argv=["net", "user", SANDBOX_USERNAME, "<redacted>", "/add"],
        )
        return SandboxIdentity(username=SANDBOX_USERNAME, password=password, created=True)

    if os.name == "posix":
        if os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandbox-user creation is not implemented.")
        if os.geteuid() != 0:
            raise RuntimeError("Creating sandbox user requires root/admin privileges on Linux.")
        subprocess.run(["userdel", "-r", SANDBOX_USERNAME], check=False, capture_output=True, text=True)
        try:
            subprocess.run(["useradd", "-m", "-s", "/bin/bash", SANDBOX_USERNAME], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to create sandbox user '{SANDBOX_USERNAME}': {exc.stderr or exc}") from exc
        return SandboxIdentity(username=SANDBOX_USERNAME, password=None, created=True)

    raise RuntimeError(f"Unsupported OS for sandbox user creation: {os.name}")


def cleanup_sandbox_identity(identity: SandboxIdentity) -> None:
    if not identity.created:
        return
    if os.name == "nt":
        proc = _run_admin_command(["net", "user", identity.username, "/delete"], allow_failure=True)
    elif os.name == "posix":
        proc = subprocess.run(["userdel", "-r", identity.username], check=False, capture_output=True, text=True)
    else:
        print(f"WARNING: could not cleanup sandbox user {identity.username}: unsupported OS")
        return
    if proc.returncode != 0:
        reason = (proc.stderr or proc.stdout or "unknown error").strip()
        print(f"WARNING: failed to delete sandbox user {identity.username}: {reason}")


def grant_task_sandbox_access(identity: SandboxIdentity, paths: list[Path]) -> None:
    if os.name == "nt":
        for path in paths:
            _run_admin_command(["icacls", str(path), "/grant", f"{identity.username}:(OI)(CI)M", "/T", "/C"])
        return

    if os.name == "posix":
        if os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandbox-user permissions are not implemented.")
        has_setfacl = shutil.which("setfacl") is not None
        for path in paths:
            if has_setfacl:
                subprocess.run(["setfacl", "-Rm", f"u:{identity.username}:rwx", str(path)], check=True, capture_output=True, text=True)
                subprocess.run(["setfacl", "-Rdm", f"u:{identity.username}:rwx", str(path)], check=True, capture_output=True, text=True)
            else:
                subprocess.run(["chmod", "-R", "a+rwX", str(path)], check=True, capture_output=True, text=True)
        return

    raise RuntimeError(f"Unsupported OS for sandbox permissions: {os.name}")


def sandbox_env(base_env: dict[str, str] | None, task_output_dir: Path) -> dict[str, str]:
    env = dict(base_env if base_env is not None else os.environ)
    runner_home = task_output_dir / "runner_home"
    runner_tmp = task_output_dir / "runner_tmp"
    runner_home.mkdir(parents=True, exist_ok=True)
    runner_tmp.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(runner_home)
    env["USERPROFILE"] = str(runner_home)
    env["TMP"] = str(runner_tmp)
    env["TEMP"] = str(runner_tmp)
    env["TMPDIR"] = str(runner_tmp)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env
