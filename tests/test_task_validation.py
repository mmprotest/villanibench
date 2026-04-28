from pathlib import Path

from villanibench.tasks.validation import validate_suite_dir, validate_task_dir


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
