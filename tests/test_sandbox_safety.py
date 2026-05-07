import json
from pathlib import Path

import pytest

from villanibench.harness.adapters.external_cli import ExternalCliAdapter
from villanibench.harness.run import run_suite
from villanibench.harness.sandbox import assert_tree_unchanged, hash_tree, prepare_sandbox
from villanibench.tasks.loader import load_task


ARTIFACTS = [".villani", ".villani_code", ".pytest_cache", "villani_debug", "logs", "result.json"]


def _write_suite(tmp_path: Path, *, repo_dir: str = "repo") -> tuple[Path, Path]:
    suite = tmp_path / "suite"
    task = suite / "tasks" / "T-001"
    (task / "repo/src").mkdir(parents=True)
    (task / "tests/visible").mkdir(parents=True)
    (task / "tests/hidden").mkdir(parents=True)
    (task / "oracle").mkdir(parents=True)
    (task / "repo/src/app.py").write_text("x=1\n", encoding="utf-8")
    (task / "prompt.txt").write_text("fix", encoding="utf-8")
    (task / "tests/visible/test_visible.py").write_text("def test_visible():\n    assert False\n", encoding="utf-8")
    (task / "tests/hidden/test_hidden.py").write_text("def test_hidden():\n    assert False\n", encoding="utf-8")
    (task / "oracle/expected_files.json").write_text("[]", encoding="utf-8")
    (task / "oracle/allowed_files.json").write_text('{"allowed_code_files":[],"forbidden_patterns":["tests/"]}', encoding="utf-8")
    (task / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")
    (task / "task.yaml").write_text(
        "\n".join(
            [
                "id: T-001",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                f"repo_dir: {repo_dir}",
                'visible_test_command: python -c "import sys; sys.exit(1)"',
                'hidden_test_command: python -c "import sys; sys.exit(1)"',
                "budget_profile: lite_v0_1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (suite / "suite.yaml").write_text(
        "\n".join(
            [
                "id: s",
                "name: s",
                "version: 0.1",
                "description: s",
                "task_count: 1",
                "categories:",
                "  - minimal_patch",
                "budget_profile: lite_v0_1",
                "visibility: mixed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return suite, task


def test_output_dir_inside_suite_rejected(tmp_path: Path):
    suite, _ = _write_suite(tmp_path)
    with pytest.raises(RuntimeError, match="--output-dir must not be inside"):
        run_suite(suite, "external_cli", "dummy", suite / "runs", {"external_cli_template": 'python -c "print(1)"'})


def test_workspace_edits_do_not_mutate_canonical_task(tmp_path: Path):
    suite, task = _write_suite(tmp_path)
    task_spec = load_task(task)
    sandbox, repo = prepare_sandbox(task_spec, tmp_path / "out" / "tasks" / "T-001")
    (repo / "src/app.py").write_text("x=2\n", encoding="utf-8")
    assert (task / "repo/src/app.py").read_text(encoding="utf-8") == "x=1\n"
    assert (sandbox / "repo/src/app.py").read_text(encoding="utf-8") == "x=2\n"


def test_parent_traversal_repo_dir_rejected(tmp_path: Path):
    _, task = _write_suite(tmp_path, repo_dir="../escape")
    task_spec = load_task(task)
    with pytest.raises(RuntimeError, match="must not contain parent traversal"):
        prepare_sandbox(task_spec, tmp_path / "out")


def test_absolute_repo_dir_rejected(tmp_path: Path):
    _, task = _write_suite(tmp_path, repo_dir="/tmp/escape")
    task_spec = load_task(task)
    with pytest.raises(RuntimeError, match="must be relative"):
        prepare_sandbox(task_spec, tmp_path / "out")


def test_symlink_inside_sandbox_rejected(tmp_path: Path, monkeypatch):
    _, task = _write_suite(tmp_path)
    task_spec = load_task(task)

    import shutil as _shutil

    original_copytree = _shutil.copytree

    def _copytree(src, dst, *args, **kwargs):
        result = original_copytree(src, dst, *args, **kwargs)
        if Path(dst).name == "repo":
            (Path(dst) / "evil_link").symlink_to(task / "prompt.txt")
        return result

    monkeypatch.setattr("villanibench.harness.sandbox.shutil.copytree", _copytree)
    with pytest.raises(RuntimeError, match="Refusing symlink"):
        prepare_sandbox(task_spec, tmp_path / "out")


def test_canonical_mutation_detected(tmp_path: Path):
    suite, task = _write_suite(tmp_path)
    baseline = hash_tree(suite)
    (task / "prompt.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Canonical benchmark suite was modified"):
        assert_tree_unchanged(suite, baseline)


def test_no_artifacts_written_inside_canonical_suite(tmp_path: Path, monkeypatch):
    suite, _ = _write_suite(tmp_path)
    adapter = ExternalCliAdapter("fake_external", 'python -c "print(1)"')
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)
    out = tmp_path / "run_out"
    run_suite(suite, "fake_external", "dummy", out, {})
    for p in suite.rglob("*"):
        assert p.name not in ARTIFACTS
    result = json.loads((out / "tasks/T-001/result.json").read_text(encoding="utf-8"))
    assert result["status"] in {"visible_failure", "harness_error", "forbidden_modification"}
