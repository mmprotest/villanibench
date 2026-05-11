from pathlib import Path

from villanibench.harness import process as p
from villanibench.harness.os_sandbox_user import SandboxIdentity


def test_windows_sandbox_launch_uses_createprocess_path(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)
    seen = {}
    monkeypatch.setattr(p, "_windows_create_process_with_logon", lambda *a, **k: seen.setdefault("called", True) or p.ProcessResult(0, "", "", False, 0.1))
    p.run_command_tree("echo hi", tmp_path, 1.0, sandbox_identity=SandboxIdentity("villanibench_sandbox", "pw"))
    assert seen.get("called") is True


def test_windows_sandbox_failure_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(p.os, "name", "nt")
    monkeypatch.setattr(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(p, "_windows_create_process_with_logon", boom)
    try:
        p.run_command_tree("echo hi", tmp_path, 1.0, sandbox_identity=SandboxIdentity("villanibench_sandbox", "pw"))
        assert False
    except RuntimeError:
        assert True
