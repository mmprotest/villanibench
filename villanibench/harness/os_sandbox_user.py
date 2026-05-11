from __future__ import annotations

import os
import secrets
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
    alphabet = string.ascii_letters + string.digits + "-_!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_sandbox_identity() -> SandboxIdentity:
    password = _generate_password()
    if os.name == "nt":
        subprocess.run(["net", "user", SANDBOX_USERNAME, "/delete"], check=False, capture_output=True, text=True)
        try:
            subprocess.run(["net", "user", SANDBOX_USERNAME, password, "/add", "/Y"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            subprocess.run(["net", "user", SANDBOX_USERNAME, password, "/add"], check=True, capture_output=True, text=True)
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
        proc = subprocess.run(["net", "user", identity.username, "/delete"], check=False, capture_output=True, text=True)
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
            subprocess.run(
                ["icacls", str(path), "/grant", f"{identity.username}:(OI)(CI)M", "/T", "/C"],
                check=True,
                capture_output=True,
                text=True,
            )
        return

    if os.name == "posix":
        if os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandbox-user permissions are not implemented.")
        for path in paths:
            subprocess.run(["chown", "-R", f"{identity.username}:{identity.username}", str(path)], check=True, capture_output=True, text=True)
            subprocess.run(["chmod", "-R", "u+rwX", str(path)], check=True, capture_output=True, text=True)
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
