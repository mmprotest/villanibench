from pathlib import Path

from villanibench.harness.os_sandbox_user import SandboxIdentity
from villanibench.harness.sandbox import prepare_sandbox


def _mk_task(tmp_path):
    tdir = tmp_path / "task"
    (tdir / "repo").mkdir(parents=True)
    (tdir / "repo" / "f.txt").write_text("x")
    (tdir / "tests" / "visible").mkdir(parents=True)
    (tdir / "tests" / "visible" / "test.txt").write_text("v")
    (tdir / "tests" / "hidden").mkdir(parents=True)
    (tdir / "tests" / "hidden" / "secret.txt").write_text("h")
    (tdir / "prompt.txt").write_text("p")
    return type("T", (), {"task_dir": tdir, "repo_dir": "repo", "prompt_file": "prompt.txt"})()


def test_prepare_sandbox_permissions(monkeypatch, tmp_path):
    task = _mk_task(tmp_path)
    out = tmp_path / "out"
    granted = {}
    monkeypatch.setattr("villanibench.harness.sandbox.grant_task_sandbox_access", lambda ident, paths, log=None: granted.setdefault("paths", paths))
    sandbox, repo = prepare_sandbox(task, out, sandbox_identity=SandboxIdentity("villanibench_sandbox", None, True))
    assert (repo / "f.txt").exists()
    assert (sandbox / "tests" / "visible" / "test.txt").exists()
    assert not (sandbox / "tests" / "hidden").exists()
    assert [p.name for p in granted["paths"]] == ["sandbox", "runner_home", "runner_tmp"]
