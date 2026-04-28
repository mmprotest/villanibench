from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
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
]

DIRTY_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
}
DIRTY_SUFFIXES = {".pyc", ".pyo", ".pyd"}
BEHAVIOR_TIMEOUT_SEC = 20


def _is_safe_repo_rel_path(path_str: str) -> bool:
    p = Path(path_str)
    if p.is_absolute():
        return False
    return ".." not in p.parts


def validate_task_dir(task_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in task_dir.rglob("*"):
        rel = path.relative_to(task_dir)
        parts = set(rel.parts)
        if any(part in DIRTY_PATH_PARTS for part in parts):
            errors.append(f"Generated artifact found in task directory: {rel.as_posix()}")
            continue
        if path.suffix in DIRTY_SUFFIXES:
            errors.append(f"Generated artifact found in task directory: {rel.as_posix()}")
            continue
        if any(part.endswith(".egg-info") for part in rel.parts):
            errors.append(f"Generated artifact found in task directory: {rel.as_posix()}")
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
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    if not prompt_path.exists() or not prompt_text.strip():
        errors.append("prompt.txt must exist and be non-empty")
    prompt_lower = prompt_text.lower()
    if "hidden test" in prompt_lower or "hidden tests" in prompt_lower:
        errors.append("prompt.txt must not mention hidden tests")
    if "oracle" in prompt_lower:
        errors.append("prompt.txt must not mention oracle")

    oracle_docs: dict[str, dict] = {}
    for rel in ["oracle/expected_files.json", "oracle/allowed_files.json", "oracle/failure_modes.json"]:
        try:
            oracle_docs[rel] = json.loads((task_dir / rel).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid JSON {rel}: {exc}")

    repo_dir = task_dir / "repo"
    expected = oracle_docs.get("oracle/expected_files.json", {})
    if not isinstance(expected, dict):
        expected = {}
    expected_files = expected.get("expected_files", []) + expected.get("strongly_expected_files", [])
    for rel_path in expected_files:
        if not _is_safe_repo_rel_path(rel_path):
            errors.append(f"Expected file path is not repo-relative safe: {rel_path}")
            continue
        if not (repo_dir / rel_path).exists():
            errors.append(f"Expected file does not exist in repo: {rel_path}")

    allowed = oracle_docs.get("oracle/allowed_files.json", {})
    if not isinstance(allowed, dict):
        allowed = {}
    allowed_files = allowed.get("allowed_code_files", [])
    for rel_path in allowed_files:
        if not _is_safe_repo_rel_path(rel_path):
            errors.append(f"allowed_code_files path must be relative and inside repo: {rel_path}")
            continue
        if not (repo_dir / rel_path).exists():
            errors.append(f"allowed_code_files path does not exist in repo: {rel_path}")

    forbidden_patterns = allowed.get("forbidden_patterns", [])
    has_test_protection = any(pattern in {"tests/", "tests", "/tests/", "\\tests\\"} for pattern in forbidden_patterns)
    if not has_test_protection:
        errors.append("Task must forbid test modifications in allowed_files.json")
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
        if not (task.budget_profile or suite.budget_profile):
            errors.append(f"{task.id}: Missing/empty resolved budget profile")
        if task.category not in suite_categories:
            errors.append(f"Task category not in suite categories: {task.id}:{task.category}")
    return errors


def _run_command(command: str, cwd: Path, timeout_sec: int) -> tuple[int, bool]:
    try:
        proc = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, timeout=timeout_sec)
        return proc.returncode, False
    except subprocess.TimeoutExpired:
        return 124, True


def validate_suite_behavior(suite_dir: Path, timeout_sec: int = BEHAVIOR_TIMEOUT_SEC) -> tuple[bool, list[dict]]:
    _, tasks = load_suite(suite_dir)
    rows: list[dict] = []
    all_ok = True
    for task in tasks:
        with tempfile.TemporaryDirectory(prefix=f"vb_behavior_{task.id}_") as temp_dir:
            sandbox = Path(temp_dir)
            shutil.copytree(task.task_dir / "repo", sandbox / "repo")
            shutil.copytree(task.task_dir / "tests" / "visible", sandbox / "tests" / "visible")
            start = time.monotonic()
            vis_code, vis_timeout = _run_command(task.visible_test_command, sandbox, timeout_sec)
            shutil.copytree(task.task_dir / "tests" / "hidden", sandbox / "tests" / "hidden")
            hid_code, hid_timeout = _run_command(task.hidden_test_command, sandbox, timeout_sec)
            elapsed = round(time.monotonic() - start, 3)
            visible_pre_fails = vis_code != 0 and not vis_timeout
            hidden_pre_fails = hid_code != 0 and not hid_timeout
            ok = visible_pre_fails and hidden_pre_fails and not vis_timeout and not hid_timeout
            all_ok = all_ok and ok
            rows.append(
                {
                    "task_id": task.id,
                    "ok": ok,
                    "visible_pre_fails": visible_pre_fails,
                    "hidden_pre_fails": hidden_pre_fails,
                    "visible_timed_out": vis_timeout,
                    "hidden_timed_out": hid_timeout,
                    "elapsed_sec": elapsed,
                }
            )
    return all_ok, rows
