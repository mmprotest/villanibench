from __future__ import annotations

import shutil
from pathlib import Path

from villanibench.tasks.schema import TaskSpec


def prepare_sandbox(task: TaskSpec, task_output_dir: Path) -> tuple[Path, Path]:
    sandbox = task_output_dir / "sandbox"
    repo_dst = sandbox / "repo"
    tests_visible_dst = sandbox / "tests" / "visible"
    tests_hidden_dst = sandbox / "tests" / "hidden"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    repo_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / task.repo_dir, repo_dst)
    tests_visible_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / "tests" / "visible", tests_visible_dst)
    tests_hidden_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.task_dir / "tests" / "hidden", tests_hidden_dst)
    shutil.copy2(task.task_dir / task.prompt_file, sandbox / "prompt.txt")
    return sandbox, repo_dst
