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
