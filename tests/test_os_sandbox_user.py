from pathlib import Path

from villanibench.harness import os_sandbox_user as m


def test_sandbox_env_sets_task_local_dirs(tmp_path):
    env = m.sandbox_env({}, tmp_path)
    assert env["HOME"] == str(tmp_path / "runner_home")
    assert env["USERPROFILE"] == str(tmp_path / "runner_home")
    assert env["TMP"] == str(tmp_path / "runner_tmp")
    assert (tmp_path / "runner_home").exists()
    assert (tmp_path / "runner_tmp").exists()


def test_create_identity_linux_order(monkeypatch):
    calls = []

    monkeypatch.setattr(m.os, "name", "posix")
    monkeypatch.setattr(m.os, "geteuid", lambda: 0)
    monkeypatch.setattr(m.os, "uname", lambda: type("U", (), {"sysname": "Linux"})())
    monkeypatch.setattr(m.subprocess, "run", lambda args, **kwargs: calls.append(args) or type("R", (), {"returncode": 0, "stderr": ""})())
    ident = m.create_sandbox_identity()
    assert ident.username == m.SANDBOX_USERNAME
    assert calls[0][:2] == ["userdel", "-r"]
    assert calls[1][:2] == ["useradd", "-m"]


def test_cleanup_warns_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(m.os, "name", "posix")
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "boom", "stdout": ""})())
    m.cleanup_sandbox_identity(m.SandboxIdentity(username=m.SANDBOX_USERNAME, password=None, created=True))
    assert "failed to delete sandbox user" in capsys.readouterr().out
