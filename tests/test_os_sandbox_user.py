from pathlib import Path

from villanibench.harness import os_sandbox_user as m


def test_sandbox_env_sets_task_local_dirs(tmp_path):
    env = m.sandbox_env({}, tmp_path)
    assert env["HOME"] == str(tmp_path / "runner_home")
    assert env["USERPROFILE"] == str(tmp_path / "runner_home")
    assert env["TMP"] == str(tmp_path / "runner_tmp")


def test_sandbox_env_preserves_path(tmp_path):
    env = m.sandbox_env({"PATH": "C:/tool/bin"}, tmp_path)
    assert env["PATH"] == "C:/tool/bin"


def test_create_identity_windows_admin_preflight(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: False)
    try:
        m.create_sandbox_identity()
        assert False
    except RuntimeError as exc:
        assert "requires an elevated Administrator shell" in str(exc)


def test_windows_create_uses_netapi_not_net_user_add(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)
    calls = []

    class Net:
        def NetUserDel(self, *_):
            calls.append("del")
            return m.NERR_UserNotFound

        def NetUserAdd(self, *_):
            calls.append("add")
            return m.NERR_Success

        def NetUserGetInfo(self, *_):
            calls.append("get")
            return m.NERR_Success

        def NetApiBufferFree(self, *_):
            return 0

    monkeypatch.setattr(m, "_netapi32", lambda: Net())
    monkeypatch.setattr(m, "_run_admin_command", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call net user add")))
    ident = m.create_sandbox_identity()
    assert ident.username == "villanibench_sandbox"
    assert calls == ["del", "add", "get"]


def test_windows_create_add_failure_raises(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)

    class Net:
        def NetUserDel(self, *_): return m.NERR_UserNotFound
        def NetUserAdd(self, *_): return 5
        def NetUserGetInfo(self, *_): return m.NERR_Success
        def NetApiBufferFree(self, *_): return 0

    monkeypatch.setattr(m, "_netapi32", lambda: Net())
    try:
        m.create_sandbox_identity()
        assert False
    except RuntimeError as exc:
        assert "NetUserAdd failed" in str(exc)


def test_windows_verify_failure_raises(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)

    class Net:
        def NetUserDel(self, *_): return m.NERR_UserNotFound
        def NetUserAdd(self, *_): return m.NERR_Success
        def NetUserGetInfo(self, *_): return m.NERR_UserNotFound
        def NetApiBufferFree(self, *_): return 0

    monkeypatch.setattr(m, "_netapi32", lambda: Net())
    try:
        m.create_sandbox_identity()
        assert False
    except RuntimeError as exc:
        assert "was not found" in str(exc)


def test_password_not_logged(monkeypatch):
    monkeypatch.setattr(m.os, "name", "nt")
    monkeypatch.setattr(m, "_is_windows_admin", lambda: True)

    class Net:
        def NetUserDel(self, *_): return m.NERR_UserNotFound
        def NetUserAdd(self, *_): return m.NERR_Success
        def NetUserGetInfo(self, *_): return m.NERR_Success
        def NetApiBufferFree(self, *_): return 0

    monkeypatch.setattr(m, "_netapi32", lambda: Net())
    logs = []
    ident = m.create_sandbox_identity(log=logs.append)
    joined = "\n".join(logs)
    assert ident.password not in joined


def test_cleanup_uses_netuserdel_and_warns_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(m.os, "name", "nt")

    class Net:
        def NetUserDel(self, *_): return 5

    monkeypatch.setattr(m, "_netapi32", lambda: Net())
    m.cleanup_sandbox_identity(m.SandboxIdentity(username=m.SANDBOX_USERNAME, password="hidden", created=True))
    assert "failed to delete sandbox user" in capsys.readouterr().out


def test_windows_password_charset():
    pw = m._generate_password(128)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    assert set(pw).issubset(allowed)


def test_icacls_calls_bounded_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(m.os, "name", "nt")
    seen = []

    def fake(argv, **kwargs):
        seen.append((argv, kwargs))
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(m, "_run_admin_command", fake)
    m.grant_task_sandbox_access(m.SandboxIdentity(username="villanibench_sandbox", password="x"), [tmp_path])
    assert seen and seen[0][0][0] == "icacls"


def test_build_sandbox_workdir_is_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(m.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    out = m.build_sandbox_workdir(Path("relative/out"), "rid-1")
    assert out.is_absolute()
    assert "villanibench" in str(out)


def test_parent_dirs_for_traverse_order(tmp_path):
    leaf = tmp_path / "a" / "b" / "c"
    parents = m.parent_dirs_for_traverse(leaf)
    assert parents
    assert parents[-1] == leaf.parent


def test_grant_parent_traverse_access_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(m.os, "name", "nt")
    calls = []
    monkeypatch.setattr(m, "_run_admin_command", lambda argv, **kwargs: calls.append(argv) or type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})())
    m.grant_parent_traverse_access(m.SandboxIdentity(username="villanibench_sandbox", password="x"), tmp_path / "one" / "two")
    assert calls
    assert all(":(RX)" in " ".join(cmd) for cmd in calls)
