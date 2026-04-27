from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ALLOWED_CATEGORIES = {
    "localisation",
    "verification",
    "state_coherence",
    "minimal_patch",
    "tool_efficiency",
    "recovery",
}

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard", "brutal"}


@dataclass
class TaskSpec:
    id: str
    title: str
    category: str
    difficulty: str
    language: str
    framework: str
    prompt_file: str
    repo_dir: str
    visible_test_command: str
    hidden_test_command: str
    budget_profile: str
    task_dir: Path


@dataclass
class SuiteSpec:
    id: str
    name: str
    version: str
    description: str
    task_count: int
    categories: list[str]
    budget_profile: str
    visibility: str
    suite_dir: Path
