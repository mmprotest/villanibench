from villanibench.harness import process as p
from villanibench.harness.os_sandbox_user import SandboxIdentity


def test_windows_structs_defined():
    assert issubclass(p.STARTUPINFOW, p.ctypes.Structure)
    assert issubclass(p.PROCESS_INFORMATION, p.ctypes.Structure)


def test_windows_sandbox_launch_uses_createprocess_path(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)
    seen = {}

    def fake(*a, **k):
        seen["called"] = True
        return p.ProcessResult(0, "", "", False, 0.1)

    monkeypatch.setattr(p, "_windows_create_process_with_logon", fake)
    p.run_command_tree("echo hi", tmp_path, 1.0, sandbox_identity=SandboxIdentity("villanibench_sandbox", "pw"))
    assert seen.get("called") is True


def test_windows_sandbox_no_unsandboxed_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)
    monkeypatch.setattr(p.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no popen")))
    monkeypatch.setattr(p, "_windows_create_process_with_logon", lambda *a, **k: p.ProcessResult(0, "", "", False, 0.1))
    p.run_command_tree("echo hi", tmp_path, 1.0, sandbox_identity=SandboxIdentity("villanibench_sandbox", "pw"))


def test_windows_timeout_calls_taskkill(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(p.subprocess, "run", fake_run)

    class FakeK32:
        def CreateFileW(self, *a): return 11
        def GetStdHandle(self, *a): return 12
        def WaitForSingleObject(self, *a): return p.WAIT_TIMEOUT
        def CloseHandle(self, *a): return 1

    class FakeAdv:
        def CreateProcessWithLogonW(self, *a):
            pi = a[-1]._obj
            pi.hProcess = 1
            pi.hThread = 1
            pi.dwProcessId = 999
            return 1

    monkeypatch.setattr(p.ctypes, "windll", type("W", (), {"kernel32": FakeK32(), "advapi32": FakeAdv()})(), raising=False)
    r = p._windows_create_process_with_logon("cmd /c echo hi", tmp_path, 0.1, {}, SandboxIdentity("villanibench_sandbox", "pw"))
    assert r.timed_out is True
    assert any(cmd[:2] == ["taskkill", "/F"] for cmd in calls)


def test_windows_cmd_executable_wrapped_for_createprocess(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)
    seen = {}

    def fake(command_line, cwd, timeout_sec, env, identity):
        seen["command_line"] = command_line
        seen["cwd"] = cwd
        return p.ProcessResult(0, "", "", False, 0.1)

    monkeypatch.setattr(p, "_windows_create_process_with_logon", fake)
    p.run_command_tree_argv([r"C:\tools\villani-code.cmd", "run", "--repo", "x"], tmp_path, 1.0, sandbox_identity=SandboxIdentity("villanibench_sandbox", "pw"))
    assert "cmd.exe" in seen["command_line"]
    assert "/d" in seen["command_line"]
    assert "/s" in seen["command_line"]
    assert "/c" in seen["command_line"]
    assert "villani-code.cmd" in seen["command_line"]
    assert seen["cwd"].is_absolute()


def test_windows_failure_message_contains_getlasterror(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(p.ctypes, "WinError", lambda code: type("E", (), {"strerror": "Access is denied."})(), raising=False)

    class FakeK32:
        def CreateFileW(self, *a): return 11
        def GetStdHandle(self, *a): return 12
        def CloseHandle(self, *a): return 1

    class FakeAdv:
        def CreateProcessWithLogonW(self, *a): return 0

    monkeypatch.setattr(p.ctypes, "WinDLL", lambda name, use_last_error=True: FakeK32() if name == "kernel32" else FakeAdv(), raising=False)
    try:
        p._windows_create_process_with_logon("C:\\x\\villani-code.exe run", tmp_path, 0.1, {}, SandboxIdentity("villanibench_sandbox", "pw"))
        assert False
    except RuntimeError as exc:
        s = str(exc)
        assert "GetLastError=5" in s
        assert "Access is denied." in s
        assert "cwd_raw=" in s
        assert "cwd_resolved=" in s
        assert "executable_raw=" in s
        assert "executable_resolved_by_which=" in s


def test_normalize_cwd_relative_and_absolute(tmp_path):
    relative = tmp_path / "artifacts" / "runs" / "test"
    relative.mkdir(parents=True)
    old_cwd = p.os.getcwd()
    try:
        p.os.chdir(tmp_path)
        raw, resolved, exists, is_dir = p._normalize_cwd(relative.relative_to(tmp_path))
    finally:
        p.os.chdir(old_cwd)
    assert raw == "artifacts/runs/test"
    assert resolved.is_absolute()
    assert exists is True
    assert is_dir is True

    raw2, resolved2, exists2, is_dir2 = p._normalize_cwd(relative)
    assert resolved2 == relative.resolve()
    assert exists2 is True
    assert is_dir2 is True


def test_resolve_executable_for_diagnostics_absolute(tmp_path):
    exe = tmp_path / "tool.exe"
    exe.write_text("x")
    raw, resolved, exists, is_file = p._resolve_executable_for_diagnostics(str(exe), {})
    assert raw == str(exe)
    assert resolved == str(exe)
    assert exists is True
    assert is_file is True


def test_resolve_executable_for_diagnostics_via_which(monkeypatch):
    monkeypatch.setattr(p.shutil, "which", lambda name, path=None: "/bin/sh" if name in ("sh", "cmd.exe") else None)
    raw, resolved, exists, _ = p._resolve_executable_for_diagnostics("sh", {})
    assert raw == "sh"
    assert resolved == "/bin/sh"
    assert isinstance(exists, bool)
