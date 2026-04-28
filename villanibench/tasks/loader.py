from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from .schema import SuiteSpec, TaskSpec


def _parse_fallback_yaml(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list_key:
            out.setdefault(current_list_key, []).append(line[4:].strip().strip('"'))
            continue
        if ":" in line and not line.startswith("  "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                out[key] = []
                current_list_key = key
            else:
                out[key] = value.strip('"')
                current_list_key = None
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        data = _parse_fallback_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be mapping: {path}")
    return data


def load_task(task_dir: Path) -> TaskSpec:
    data = _read_yaml(task_dir / "task.yaml")
    return TaskSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        category=str(data["category"]),
        difficulty=str(data["difficulty"]),
        language=str(data["language"]),
        framework=str(data["framework"]),
        prompt_file=str(data["prompt_file"]),
        repo_dir=str(data["repo_dir"]),
        visible_test_command=str(data["visible_test_command"]),
        hidden_test_command=str(data["hidden_test_command"]),
        budget_profile=str(data.get("budget_profile") or "") or None,
        task_dir=task_dir,
    )


def load_suite(suite_dir: Path) -> tuple[SuiteSpec, list[TaskSpec]]:
    data = _read_yaml(suite_dir / "suite.yaml")
    spec = SuiteSpec(
        id=str(data["id"]),
        name=str(data["name"]),
        version=str(data["version"]),
        description=str(data["description"]),
        task_count=int(data["task_count"]),
        categories=list(data["categories"]),
        budget_profile=str(data.get("budget_profile") or ""),
        visibility=str(data["visibility"]),
        suite_dir=suite_dir,
    )
    tasks_root = suite_dir / "tasks"
    tasks = [load_task(p) for p in sorted(tasks_root.iterdir()) if p.is_dir()]
    return spec, tasks
