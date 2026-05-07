from pathlib import Path

import pytest

from villanibench.harness.docker import build_docker_argv
from villanibench.harness.sandbox import _safe_copytree


def test_docker_argv_mounts_only_workspace(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    argv = build_docker_argv(
        image="agent:latest",
        host_workspace_dir=workspace,
        command_argv=["python", "-V"],
    )
    joined = " ".join(argv)
    assert "dst=/workspace" in joined
    assert str(workspace.resolve()) in joined
    assert "--network" in argv and "none" in argv
    assert "--read-only" in argv


def test_docker_argv_does_not_include_suite_root(tmp_path: Path):
    suite_root = tmp_path / "suite"
    suite_root.mkdir()
    workspace = tmp_path / "copy"
    workspace.mkdir()
    argv = build_docker_argv(image="agent:latest", host_workspace_dir=workspace, command_argv=["echo", "ok"])
    assert str(suite_root.resolve()) not in " ".join(argv)


def test_copy_rejects_symlink(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "f.txt").write_text("ok", encoding="utf-8")
    (src / "link").symlink_to(src / "f.txt")
    with pytest.raises(RuntimeError, match="Refusing symlink"):
        _safe_copytree(src, dst, dst)
