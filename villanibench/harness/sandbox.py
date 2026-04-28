from __future__ import annotations

import shutil
from pathlib import Path

from villanibench.tasks.schema import TaskSpec


def copy_visible_tests_to_sandbox(task: TaskSpec, sandbox_dir: Path) -> Path:
    tests_visible_dst = sandbox_dir / "tests" / "visible"
    tests_visible_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / "tests" / "visible", tests_visible_dst)
    return tests_visible_dst


def copy_hidden_tests_to_sandbox_for_evaluation(task: TaskSpec, sandbox_dir: Path) -> Path:
    tests_hidden_dst = sandbox_dir / "tests" / "hidden"
    if tests_hidden_dst.exists():
        raise RuntimeError("Runner created tests/hidden before evaluator copied hidden tests.")
    tests_hidden_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / "tests" / "hidden", tests_hidden_dst)
    return tests_hidden_dst


def prepare_sandbox(task: TaskSpec, task_output_dir: Path) -> tuple[Path, Path]:
    sandbox = task_output_dir / "sandbox"
    repo_dst = sandbox / "repo"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    repo_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / task.repo_dir, repo_dst)
    copy_visible_tests_to_sandbox(task, sandbox)
    shutil.copy2(task.task_dir / task.prompt_file, sandbox / "prompt.txt")
    return sandbox, repo_dst
