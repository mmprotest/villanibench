from pathlib import Path

import pytest

from villanibench.cli import main
from villanibench.tasks.validation import validate_suite_behavior, validate_suite_dir, validate_task_dir


def test_task_validation_ok():
    errors = validate_task_dir(Path("suites/core_v0_1/tasks/VB-MIN-001"))
    assert errors == []


def test_task_validation_rejects_generated_artifacts(tmp_path: Path):
    task_dir = tmp_path / "T-001"
    (task_dir / "repo/src/foo/__pycache__").mkdir(parents=True)
    (task_dir / "tests/visible").mkdir(parents=True)
    (task_dir / "tests/hidden").mkdir(parents=True)
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "prompt.txt").write_text("fix", encoding="utf-8")
    (task_dir / "task.yaml").write_text(
        "\n".join(
            [
                "id: T-001",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                "repo_dir: repo",
                "visible_test_command: pytest -q tests/visible",
                "hidden_test_command: pytest -q tests/hidden",
                "budget_profile: lite_v0_1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for rel in ["oracle/expected_files.json", "oracle/allowed_files.json", "oracle/failure_modes.json"]:
        (task_dir / rel).write_text("[]", encoding="utf-8")
    (task_dir / "repo/src/foo/__pycache__/x.pyc").write_bytes(b"123")
    errors = validate_task_dir(task_dir)
    assert any("Generated artifact found in task directory" in e for e in errors)


def test_suite_validation_clean_for_core_suite():
    errors = validate_suite_dir(Path("suites/core_v0_1"))
    assert errors == []


def _write_min_task(tmp_path: Path, *, expected_file: str = "src/app.py", allowed_files: list[str] | None = None, forbidden_patterns: list[str] | None = None, prompt: str = "fix it") -> Path:
    task_dir = tmp_path / "T-002"
    (task_dir / "repo/src").mkdir(parents=True)
    (task_dir / "repo/src/app.py").write_text("x=1\n", encoding="utf-8")
    (task_dir / "tests/visible").mkdir(parents=True)
    (task_dir / "tests/hidden").mkdir(parents=True)
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (task_dir / "task.yaml").write_text(
        "\n".join(
            [
                "id: T-002",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                "repo_dir: repo",
                "visible_test_command: pytest -q tests/visible",
                "hidden_test_command: pytest -q tests/hidden",
                "budget_profile: lite_v0_1",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    (task_dir / "oracle/expected_files.json").write_text(
        f'{{"expected_files":["{expected_file}"],"strongly_expected_files":[]}}',
        encoding="utf-8",
    )
    af = allowed_files or ["src/app.py"]
    fp = forbidden_patterns or ["tests/"]
    (task_dir / "oracle/allowed_files.json").write_text(
        '{"allowed_code_files":' + str(af).replace("'", '"') + ',"forbidden_files":[],"forbidden_patterns":' + str(fp).replace("'", '"') + "}",
        encoding="utf-8",
    )
    (task_dir / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")
    return task_dir


def test_validation_fails_when_expected_file_missing(tmp_path: Path):
    task_dir = _write_min_task(tmp_path, expected_file="src/missing.py")
    errors = validate_task_dir(task_dir)
    assert any("Expected file does not exist in repo: src/missing.py" in e for e in errors)


def test_validation_fails_for_allowed_files_outside_repo(tmp_path: Path):
    task_dir = _write_min_task(tmp_path, allowed_files=["../outside.py"])
    errors = validate_task_dir(task_dir)
    assert any("allowed_code_files path must be relative and inside repo" in e for e in errors)


def test_validation_fails_without_test_forbidden_pattern(tmp_path: Path):
    task_dir = _write_min_task(tmp_path, forbidden_patterns=["docs/"])
    errors = validate_task_dir(task_dir)
    assert "Task must forbid test modifications in allowed_files.json" in errors


def test_validation_fails_when_prompt_mentions_hidden_tests(tmp_path: Path):
    task_dir = _write_min_task(tmp_path, prompt="please pass hidden tests too")
    errors = validate_task_dir(task_dir)
    assert "prompt.txt must not mention hidden tests" in errors


def _write_behavior_suite(tmp_path: Path, *, visible_passes: bool = False, hidden_passes: bool = False, hang: bool = False) -> Path:
    suite_dir = tmp_path / "suite"
    task_dir = suite_dir / "tasks" / "VB-T-001"
    (task_dir / "repo/src").mkdir(parents=True)
    (task_dir / "tests/visible").mkdir(parents=True)
    (task_dir / "tests/hidden").mkdir(parents=True)
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "repo/src/app.py").write_text("def x():\n    return 1\n", encoding="utf-8")
    (task_dir / "prompt.txt").write_text("fix bug", encoding="utf-8")
    (task_dir / "task.yaml").write_text(
        "\n".join(
            [
                "id: VB-T-001",
                "title: t",
                "category: minimal_patch",
                "difficulty: easy",
                "language: python",
                "framework: pytest",
                "prompt_file: prompt.txt",
                "repo_dir: repo",
                "visible_test_command: pytest -q tests/visible",
                "hidden_test_command: pytest -q tests/hidden",
                "budget_profile: lite_v0_1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (task_dir / "oracle/expected_files.json").write_text('{"expected_files":["src/app.py"],"strongly_expected_files":[]}', encoding="utf-8")
    (task_dir / "oracle/allowed_files.json").write_text(
        '{"allowed_code_files":["src/app.py"],"forbidden_patterns":["tests/"]}',
        encoding="utf-8",
    )
    (task_dir / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")
    if hang:
        body = "import time\n\ndef test_hang():\n    time.sleep(60)\n"
        (task_dir / "tests/visible/test_visible.py").write_text(body, encoding="utf-8")
        (task_dir / "tests/hidden/test_hidden.py").write_text(body, encoding="utf-8")
    else:
        (task_dir / "tests/visible/test_visible.py").write_text(
            f"def test_visible():\n    assert {str(visible_passes)}\n",
            encoding="utf-8",
        )
        (task_dir / "tests/hidden/test_hidden.py").write_text(
            f"def test_hidden():\n    assert {str(hidden_passes)}\n",
            encoding="utf-8",
        )
    (suite_dir / "suite.yaml").write_text(
        "\n".join(
            [
                "id: x",
                "name: x",
                "version: 0.1",
                "description: x",
                "task_count: 1",
                "categories:",
                "  - minimal_patch",
                "budget_profile: lite_v0_1",
                "visibility: private",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return suite_dir


def test_behavior_validation_passes_when_visible_and_hidden_fail(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=False, hidden_passes=False)
    ok, rows = validate_suite_behavior(suite, timeout_sec=5)
    assert ok is True
    assert rows[0]["visible_pre_fails"] is True
    assert rows[0]["hidden_pre_fails"] is True


def test_behavior_validation_fails_when_hidden_passes(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=False, hidden_passes=True)
    ok, rows = validate_suite_behavior(suite, timeout_sec=5)
    assert ok is False
    assert rows[0]["hidden_pre_fails"] is False


def test_behavior_validation_fails_when_visible_passes(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=True, hidden_passes=False)
    ok, rows = validate_suite_behavior(suite, timeout_sec=5)
    assert ok is False
    assert rows[0]["visible_pre_fails"] is False


def test_behavior_validation_fails_fast_on_timeout(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, hang=True)
    ok, rows = validate_suite_behavior(suite, timeout_sec=1)
    assert ok is False
    assert rows[0]["visible_timed_out"] is True


def test_validate_behavior_cli_exits_non_zero_on_failure(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=True, hidden_passes=False)
    with pytest.raises(SystemExit) as exc:
        main(["validate-behavior", str(suite)])
    assert exc.value.code == 1


def test_validate_behavior_cli_accepts_timeout_sec(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=False, hidden_passes=False)
    main(["validate-behavior", str(suite), "--timeout-sec", "5"])



def test_behavior_validation_fails_on_test_syntax_error(tmp_path: Path):
    suite = _write_behavior_suite(tmp_path, visible_passes=False, hidden_passes=False)
    visible_test = suite / "tasks" / "VB-T-001" / "tests" / "visible" / "test_visible.py"
    visible_test.write_text("def test_visible()\n    assert False\n", encoding="utf-8")
    ok, rows = validate_suite_behavior(suite, timeout_sec=5)
    assert ok is False
    assert rows[0]["message"] is not None
    assert "Task test infrastructure error before fix" in rows[0]["message"]
