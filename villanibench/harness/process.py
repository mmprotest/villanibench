from __future__ import annotations

import ctypes
import os
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from villanibench.harness.os_sandbox_user import SandboxIdentity

STARTF_USESTDHANDLES = 0x00000100
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NEW_PROCESS_GROUP = 0x00000200
LOGON_WITH_PROFILE = 0x00000001
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
STD_INPUT_HANDLE = -10


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", ctypes.c_uint32), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", ctypes.c_int)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32), ("lpReserved", ctypes.c_wchar_p), ("lpDesktop", ctypes.c_wchar_p), ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_uint32), ("dwY", ctypes.c_uint32), ("dwXSize", ctypes.c_uint32), ("dwYSize", ctypes.c_uint32),
        ("dwXCountChars", ctypes.c_uint32), ("dwYCountChars", ctypes.c_uint32), ("dwFillAttribute", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32), ("wShowWindow", ctypes.c_ushort), ("cbReserved2", ctypes.c_ushort),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)), ("hStdInput", ctypes.c_void_p), ("hStdOutput", ctypes.c_void_p), ("hStdError", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", ctypes.c_void_p), ("hThread", ctypes.c_void_p), ("dwProcessId", ctypes.c_uint32), ("dwThreadId", ctypes.c_uint32)]


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

def _build_unicode_env_block(env: dict[str, str] | None) -> ctypes.Array[ctypes.c_wchar] | None:
    if env is None:
        return None
    block = "".join(f"{k}={v}\0" for k, v in sorted(env.items())) + "\0"
    return ctypes.create_unicode_buffer(block)

def _windows_create_process_with_logon(command_line: str, cwd: Path, timeout_sec: float, env: dict[str, str] | None, identity: SandboxIdentity) -> ProcessResult:
    if not identity.password:
        raise RuntimeError("Windows sandbox launch requires sandbox identity password.")
    runner_tmp = cwd.parent / "runner_tmp"
    if not runner_tmp.exists():
        runner_tmp = cwd / ".runner_tmp"
    runner_tmp.mkdir(parents=True, exist_ok=True)
    stdout_path = runner_tmp / f"proc_out_{time.time_ns()}.log"
    stderr_path = runner_tmp / f"proc_err_{time.time_ns()}.log"

    k32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32

    sa = SECURITY_ATTRIBUTES(nLength=ctypes.sizeof(SECURITY_ATTRIBUTES), lpSecurityDescriptor=None, bInheritHandle=1)
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x1
    CREATE_ALWAYS = 2
    FILE_ATTRIBUTE_NORMAL = 0x80

    CreateFileW = k32.CreateFileW
    if hasattr(CreateFileW, "restype"):
        CreateFileW.restype = ctypes.c_void_p
    out_h = CreateFileW(str(stdout_path), GENERIC_WRITE, FILE_SHARE_READ, ctypes.byref(sa), CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    err_h = CreateFileW(str(stderr_path), GENERIC_WRITE, FILE_SHARE_READ, ctypes.byref(sa), CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    if out_h in (0, ctypes.c_void_p(-1).value) or err_h in (0, ctypes.c_void_p(-1).value):
        raise RuntimeError("Failed to create output capture files for Windows sandbox process.")

    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(STARTUPINFOW)
    startup.dwFlags |= STARTF_USESTDHANDLES
    startup.hStdOutput = out_h
    startup.hStdError = err_h
    startup.hStdInput = k32.GetStdHandle(STD_INPUT_HANDLE)
    pi = PROCESS_INFORMATION()

    lp_environment = _build_unicode_env_block(env)
    start = time.monotonic()
    timed_out = False
    try:
        ok = advapi32.CreateProcessWithLogonW(identity.username, ".", identity.password, LOGON_WITH_PROFILE, None, ctypes.c_wchar_p(command_line), CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_PROCESS_GROUP, lp_environment, str(cwd), ctypes.byref(startup), ctypes.byref(pi))
        if not ok:
            raise RuntimeError(f"Failed to launch sandboxed process as {identity.username}.")
        wait_res = k32.WaitForSingleObject(pi.hProcess, int(timeout_sec * 1000))
        if wait_res == WAIT_TIMEOUT:
            timed_out = True
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pi.dwProcessId)], capture_output=True, **_subprocess_text_kwargs())
            k32.WaitForSingleObject(pi.hProcess, 3000)
            exit_code = 124
        elif wait_res == WAIT_OBJECT_0:
            code = ctypes.c_uint32(0)
            k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            exit_code = int(code.value)
        else:
            raise RuntimeError(f"WaitForSingleObject failed with status {wait_res}.")
    finally:
        k32.CloseHandle(out_h)
        k32.CloseHandle(err_h)
        if pi.hThread:
            k32.CloseHandle(pi.hThread)
        if pi.hProcess:
            k32.CloseHandle(pi.hProcess)

    out = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    err = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    if timed_out:
        err = f"{err.rstrip()}\nCommand timed out after {timeout_sec:.1f}s and was terminated.".strip()
    return ProcessResult(exit_code, out, err, timed_out, time.monotonic() - start)

def run_command_tree(command: str, cwd: Path, timeout_sec: float, env: dict[str, str] | None = None, sandbox_identity: SandboxIdentity | None = None) -> ProcessResult:
    start = time.monotonic()
    kwargs = _popen_kwargs(cwd, env)
    if sandbox_identity is None:
        proc = subprocess.Popen(command, shell=True, **kwargs)
        try:
            out, err = proc.communicate(timeout=timeout_sec)
            return ProcessResult(proc.returncode or 0, out or "", err or "", False, time.monotonic() - start)
        except subprocess.TimeoutExpired:
            out, err, _ = _timeout_cleanup(proc, timeout_sec)
            return ProcessResult(124, out, err, True, time.monotonic() - start)

    if os.name == "nt":
        cmdline = subprocess.list2cmdline(["cmd.exe", "/d", "/s", "/c", command])
        return _windows_create_process_with_logon(cmdline, cwd, timeout_sec, env, sandbox_identity)
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

def run_command_tree_argv(argv: list[str], cwd: Path, timeout_sec: float, env: dict[str, str] | None = None, stdin_text: str | None = None, sandbox_identity: SandboxIdentity | None = None) -> ProcessResult:
    start = time.monotonic()
    kwargs = _popen_kwargs(cwd, env)
    cmd_argv = argv
    if sandbox_identity is not None:
        if os.name == "nt":
            if argv and argv[0].lower().endswith((".cmd", ".bat")):
                wrapped = f'"{argv[0]}"'
                if len(argv) > 1:
                    wrapped = f"{wrapped} {subprocess.list2cmdline(argv[1:])}"
                cmdline = subprocess.list2cmdline(["cmd.exe", "/d", "/s", "/c", wrapped])
            else:
                cmdline = subprocess.list2cmdline(argv)
            return _windows_create_process_with_logon(cmdline, cwd, timeout_sec, env, sandbox_identity)
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
