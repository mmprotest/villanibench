from pathlib import Path
import subprocess

from villanibench.harness import os_sandbox_user as m


def test_sandbox_env_sets_task_local_dirs(tmp_path):
    env = m.sandbox_env({}, tmp_path)
    assert env["HOME"] == str(tmp_path / "runner_home")
    assert env["USERPROFILE"] == str(tmp_path / "runner_home")
    assert env["TMP"] == str(tmp_path / "runner_tmp")


def test_create_identity_windows_admin_preflight(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: False)
    try:
        m.create_sandbox_identity()
        assert False
    except RuntimeError as exc:
        assert "requires an elevated Administrator shell" in str(exc)


def test_create_identity_windows_uses_fixed_username_and_timeouts(monkeypatch):
    calls = []
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ident = m.create_sandbox_identity()
    assert ident.username == "villanibench_sandbox"
    assert calls[0][0] == ["net", "user", "villanibench_sandbox", "/delete"]
    assert calls[0][1]["timeout"] == 20.0
    assert calls[1][0][0:3] == ["net", "user", "villanibench_sandbox"]


def test_create_identity_windows_timeout_raises(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)

    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs["timeout"])

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    try:
        m.create_sandbox_identity()
        assert False
    except RuntimeError as exc:
        assert "timed out" in str(exc)


def test_windows_password_charset():
    pw = m._generate_password(128)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    assert set(pw).issubset(allowed)


def test_cleanup_warns_on_failure_and_does_not_raise(monkeypatch, capsys):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(
        m,
        "_run_admin_command",
        lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "boom", "stdout": ""})(),
    )
    m.cleanup_sandbox_identity(m.SandboxIdentity(username=m.SANDBOX_USERNAME, password="hidden", created=True))
    assert "failed to delete sandbox user" in capsys.readouterr().out


def test_icacls_calls_bounded_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(m.os, "name", "nt")
    seen = []

    def fake(argv, **kwargs):
        seen.append((argv, kwargs))
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(m, "_run_admin_command", fake)
    m.grant_task_sandbox_access(m.SandboxIdentity(username="villanibench_sandbox", password="x"), [tmp_path])
    assert seen and seen[0][0][0] == "icacls"
