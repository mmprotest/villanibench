from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from villanibench.tasks.schema import TaskSpec


def assert_under(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise RuntimeError(f"Path escapes sandbox: {resolved} not under {root_resolved}")
    return resolved


def reject_absolute_or_parent_path(value: str | Path, *, field_name: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        raise RuntimeError(f"{field_name} must be relative, got absolute path: {value}")
    if ".." in p.parts:
        raise RuntimeError(f"{field_name} must not contain parent traversal: {value}")
    return p


def hash_tree(root: Path) -> dict[str, str]:
    root = root.resolve()
    hashes: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            rel = p.relative_to(root).as_posix()
            hashes[rel] = "SYMLINK:" + str(p.readlink())
            continue
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def diff_hashes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]


def assert_tree_unchanged(root: Path, before: dict[str, str]) -> None:
    after = hash_tree(root)
    changed = diff_hashes(before, after)
    if changed:
        preview = "\n".join(changed[:25])
        extra = "" if len(changed) <= 25 else f"\n... and {len(changed) - 25} more"
        raise RuntimeError(
            "Canonical benchmark suite was modified during run.\n"
            f"Changed files:\n{preview}{extra}"
        )


def _assert_no_symlinks(root: Path) -> None:
    for p in root.rglob("*"):
        if p.is_symlink():
            raise RuntimeError(f"Refusing symlink inside benchmark sandbox: {p}")


def copy_visible_tests_to_sandbox(task: TaskSpec, sandbox_dir: Path) -> Path:
    task_root = task.task_dir.resolve()
    tests_visible_src = assert_under(task_root / "tests" / "visible", task_root)
    tests_visible_dst = assert_under(sandbox_dir / "tests" / "visible", sandbox_dir)
    tests_visible_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tests_visible_src, tests_visible_dst)
    return tests_visible_dst


def copy_hidden_tests_to_sandbox_for_evaluation(task: TaskSpec, sandbox_dir: Path) -> Path:
    task_root = task.task_dir.resolve()
    tests_hidden_src = assert_under(task_root / "tests" / "hidden", task_root)
    tests_hidden_dst = assert_under(sandbox_dir / "tests" / "hidden", sandbox_dir)
    if tests_hidden_dst.exists():
        raise RuntimeError("Runner created tests/hidden before evaluator copied hidden tests.")
    tests_hidden_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tests_hidden_src, tests_hidden_dst)
    _assert_no_symlinks(sandbox_dir)
    return tests_hidden_dst


def prepare_sandbox(task: TaskSpec, task_output_dir: Path) -> tuple[Path, Path]:
    task_root = task.task_dir.resolve()
    output_root = task_output_dir.resolve()
    sandbox = assert_under(output_root / "sandbox", output_root)
    repo_dst = sandbox / "repo"
    repo_rel = reject_absolute_or_parent_path(task.repo_dir, field_name="repo_dir")
    prompt_rel = reject_absolute_or_parent_path(task.prompt_file, field_name="prompt_file")
    repo_src = assert_under(task_root / repo_rel, task_root)
    prompt_src = assert_under(task_root / prompt_rel, task_root)
    if sandbox.exists():
        shutil.rmtree(sandbox)
    repo_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_src, repo_dst)
    copy_visible_tests_to_sandbox(task, sandbox)
    shutil.copy2(prompt_src, assert_under(sandbox / "prompt.txt", sandbox))
    _assert_no_symlinks(sandbox)
    return sandbox, repo_dst
