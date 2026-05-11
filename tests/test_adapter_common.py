import os

import pytest

from villanibench.harness.adapters.common import resolve_executable_for_sandbox


def test_resolve_executable_uses_which(monkeypatch):
    monkeypatch.setattr("villanibench.harness.adapters.common.shutil.which", lambda cmd, path=None: "/bin/villani-code")
    resolved = resolve_executable_for_sandbox("villani-code", {"PATH": "/bin"})
    assert resolved == os.path.abspath("/bin/villani-code")


def test_resolve_executable_absolute_path(tmp_path):
    exe = tmp_path / "villani-code"
    exe.write_text("x", encoding="utf-8")
    assert resolve_executable_for_sandbox(str(exe)) == str(exe)


def test_resolve_executable_missing_raises(monkeypatch):
    monkeypatch.setattr("villanibench.harness.adapters.common.shutil.which", lambda cmd, path=None: None)
    with pytest.raises(RuntimeError, match="Agent executable could not be resolved before sandbox launch"):
        resolve_executable_for_sandbox("villani-code", {"PATH": ""})
