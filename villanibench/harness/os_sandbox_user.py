from __future__ import annotations

import ctypes
import os
import secrets
import shutil
import string
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SANDBOX_USERNAME = "villanibench_sandbox"

USER_PRIV_USER = 1
UF_SCRIPT = 0x0001
UF_NORMAL_ACCOUNT = 0x0200
UF_DONT_EXPIRE_PASSWD = 0x10000
NERR_Success = 0
NERR_UserNotFound = 2221


class USER_INFO_1(ctypes.Structure):
    _fields_ = [
        ("usri1_name", ctypes.c_wchar_p),
        ("usri1_password", ctypes.c_wchar_p),
        ("usri1_password_age", ctypes.c_uint32),
        ("usri1_priv", ctypes.c_uint32),
        ("usri1_home_dir", ctypes.c_wchar_p),
        ("usri1_comment", ctypes.c_wchar_p),
        ("usri1_flags", ctypes.c_uint32),
        ("usri1_script_path", ctypes.c_wchar_p),
    ]


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


def _netapi32():
    return ctypes.windll.netapi32


def _windows_user_exists(username: str) -> bool:
    bufptr = ctypes.c_void_p()
    status = _netapi32().NetUserGetInfo(None, username, 1, ctypes.byref(bufptr))
    try:
        if status == NERR_Success:
            return True
        if status == NERR_UserNotFound:
            return False
        raise RuntimeError(f"NetUserGetInfo failed for '{username}' with status {status}.")
    finally:
        if bufptr.value:
            _netapi32().NetApiBufferFree(bufptr)


def create_sandbox_identity(log: Callable[[str], None] | None = None) -> SandboxIdentity:
    def _emit(msg: str) -> None:
        if log is not None:
            log(msg)

    password = _generate_password()
    if os.name == "nt":
        _emit(f"[sandbox-user] admin check start username={SANDBOX_USERNAME}")
        is_admin = _is_windows_admin()
        _emit(f"[sandbox-user] admin check done username={SANDBOX_USERNAME} passed={is_admin}")
        if not is_admin:
            raise RuntimeError("Creating sandbox user 'villanibench_sandbox' requires an elevated Administrator shell on Windows.")
        _emit(f"[sandbox-user] stale delete start username={SANDBOX_USERNAME} method=netapi32")
        delete_status = _netapi32().NetUserDel(None, SANDBOX_USERNAME)
        _emit(f"[sandbox-user] stale delete done username={SANDBOX_USERNAME} method=netapi32 attempted=True status={delete_status}")
        if delete_status not in (NERR_Success, NERR_UserNotFound):
            raise RuntimeError(f"Failed stale sandbox-user delete for '{SANDBOX_USERNAME}' with status {delete_status}.")

        info = USER_INFO_1(
            usri1_name=SANDBOX_USERNAME,
            usri1_password=password,
            usri1_password_age=0,
            usri1_priv=USER_PRIV_USER,
            usri1_home_dir=None,
            usri1_comment=None,
            usri1_flags=UF_SCRIPT | UF_NORMAL_ACCOUNT | UF_DONT_EXPIRE_PASSWD,
            usri1_script_path=None,
        )
        param_err = ctypes.c_uint32(0)
        _emit(f"[sandbox-user] create start username={SANDBOX_USERNAME} method=netapi32")
        create_status = _netapi32().NetUserAdd(None, 1, ctypes.byref(info), ctypes.byref(param_err))
        _emit(f"[sandbox-user] create done username={SANDBOX_USERNAME} method=netapi32 status={create_status} succeeded={create_status == NERR_Success}")
        if create_status != NERR_Success:
            raise RuntimeError(f"NetUserAdd failed for '{SANDBOX_USERNAME}' with status {create_status} (param_err={param_err.value}).")

        _emit(f"[sandbox-user] verify start username={SANDBOX_USERNAME} method=netapi32")
        if not _windows_user_exists(SANDBOX_USERNAME):
            raise RuntimeError(f"NetUserAdd reported success but user '{SANDBOX_USERNAME}' was not found.")
        _emit(f"[sandbox-user] verify done username={SANDBOX_USERNAME} method=netapi32")
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
        status = _netapi32().NetUserDel(None, identity.username)
        if status not in (NERR_Success, NERR_UserNotFound):
            print(f"WARNING: failed to delete sandbox user {identity.username}: netapi32 status={status}")
        return
    if os.name == "posix":
        proc = subprocess.run(["userdel", "-r", identity.username], check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            reason = (proc.stderr or proc.stdout or "unknown error").strip()
            print(f"WARNING: failed to delete sandbox user {identity.username}: {reason}")
        return
    print(f"WARNING: could not cleanup sandbox user {identity.username}: unsupported OS")




def build_sandbox_workdir(output_dir: Path, run_id: str) -> Path:
    root = Path(tempfile.gettempdir()) / "villanibench" / "sandbox"
    return (root / run_id).resolve()


def parent_dirs_for_traverse(path: Path) -> list[Path]:
    resolved = path.resolve()
    parents = list(resolved.parents)
    parents.reverse()
    return parents


def grant_parent_traverse_access(identity: SandboxIdentity, path: Path, log: Callable[[str], None] | None = None) -> None:
    def _emit(msg: str) -> None:
        if log is not None:
            log(msg)

    if os.name != "nt":
        return
    for parent in parent_dirs_for_traverse(path):
        _emit(f"[sandbox-user] access grant start username={identity.username} path={parent} mode=read_execute")
        try:
            _run_admin_command(["icacls", str(parent), "/grant", f"{identity.username}:(RX)", "/C"])
            _emit(f"[sandbox-user] access grant done username={identity.username} path={parent}")
        except Exception as exc:
            _emit(f"[sandbox-user] access grant failed username={identity.username} path={parent} error={exc}")
            raise

def grant_task_sandbox_access(identity: SandboxIdentity, paths: list[Path], log: Callable[[str], None] | None = None) -> None:
    def _emit(msg: str) -> None:
        if log is not None:
            log(msg)
    failed = 0
    if os.name == "nt":
        for path in paths:
            _emit(f"[sandbox-user] access grant start username={identity.username} path={path} mode=modify")
            try:
                grant_parent_traverse_access(identity, path, log=log)
                _run_admin_command(["icacls", str(path), "/grant", f"{identity.username}:(OI)(CI)M", "/T", "/C"])
                _emit(f"[sandbox-user] access grant done username={identity.username} path={path}")
            except Exception as exc:
                failed += 1
                _emit(f"[sandbox-user] access grant failed username={identity.username} path={path} error_type={type(exc).__name__} error={exc}")
                raise
        _emit(f"[sandbox-user] access summary username={identity.username} grants={len(paths)} failed={failed}")
        return

    if os.name == "posix":
        if os.uname().sysname == "Darwin":
            raise RuntimeError("macOS sandbox-user permissions are not implemented.")
        has_setfacl = shutil.which("setfacl") is not None
        for path in paths:
            _emit(f"[sandbox-user] access grant start username={identity.username} path={path} mode=read_write_execute")
            if has_setfacl:
                subprocess.run(["setfacl", "-Rm", f"u:{identity.username}:rwx", str(path)], check=True, capture_output=True, text=True)
                subprocess.run(["setfacl", "-Rdm", f"u:{identity.username}:rwx", str(path)], check=True, capture_output=True, text=True)
            else:
                subprocess.run(["chmod", "-R", "a+rwX", str(path)], check=True, capture_output=True, text=True)
            _emit(f"[sandbox-user] access grant done username={identity.username} path={path}")
        _emit(f"[sandbox-user] access summary username={identity.username} grants={len(paths)} failed={failed}")
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
