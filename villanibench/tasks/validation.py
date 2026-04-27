from __future__ import annotations

import json
from pathlib import Path

from .loader import load_suite, load_task
from .schema import ALLOWED_CATEGORIES, ALLOWED_DIFFICULTIES


REQUIRED_TASK_FILES = [
    "task.yaml",
    "prompt.txt",
    "repo",
    "tests/visible",
    "tests/hidden",
    "oracle/expected_files.json",
    "oracle/allowed_files.json",
    "oracle/failure_modes.json",
]


REQUIRED_TASK_FIELDS = [
    "id",
    "title",
    "category",
    "difficulty",
    "language",
    "framework",
    "prompt_file",
    "repo_dir",
    "visible_test_command",
    "hidden_test_command",
    "budget_profile",
]


def validate_task_dir(task_dir: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_TASK_FILES:
        if not (task_dir / rel).exists():
            errors.append(f"Missing required file/dir: {rel}")
    try:
        task = load_task(task_dir)
    except Exception as exc:
        return errors + [f"task.yaml parse/load error: {exc}"]

    for field in REQUIRED_TASK_FIELDS:
        if not getattr(task, field):
            errors.append(f"Missing/empty task field: {field}")

    if task.category not in ALLOWED_CATEGORIES:
        errors.append(f"Invalid category: {task.category}")
    if task.difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(f"Invalid difficulty: {task.difficulty}")
    if task.id != task_dir.name:
        errors.append("Task id must match directory name")

    prompt_path = task_dir / task.prompt_file
    if not prompt_path.exists() or not prompt_path.read_text(encoding="utf-8").strip():
        errors.append("prompt.txt must exist and be non-empty")

    for rel in ["oracle/expected_files.json", "oracle/allowed_files.json", "oracle/failure_modes.json"]:
        try:
            json.loads((task_dir / rel).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON {rel}: {exc}")
    return errors


def validate_suite_dir(suite_dir: Path) -> list[str]:
    errors: list[str] = []
    suite_yaml = suite_dir / "suite.yaml"
    if not suite_yaml.exists():
        return ["Missing suite.yaml"]
    try:
        suite, tasks = load_suite(suite_dir)
    except Exception as exc:
        return [f"suite.yaml parse/load error: {exc}"]

    for field in ["id", "name", "version", "description", "task_count", "categories", "budget_profile", "visibility"]:
        if getattr(suite, field) in (None, "", []):
            errors.append(f"Missing/empty suite field: {field}")

    if suite.task_count != len(tasks):
        errors.append(f"task_count mismatch: suite says {suite.task_count}, found {len(tasks)}")

    suite_categories = set(suite.categories)
    for task in tasks:
        task_errors = validate_task_dir(task.task_dir)
        errors.extend([f"{task.id}: {e}" for e in task_errors])
        if task.category not in suite_categories:
            errors.append(f"Task category not in suite categories: {task.id}:{task.category}")
    return errors
