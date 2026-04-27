from pathlib import Path

from villanibench.tasks.validation import validate_task_dir


def test_task_validation_ok():
    errors = validate_task_dir(Path("suites/core_v0_1/tasks/VB-MIN-001"))
    assert errors == []
