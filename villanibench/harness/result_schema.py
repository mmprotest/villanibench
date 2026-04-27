from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaskResult:
    schema_version: str = "0.1"
    run_id: str = ""
    suite_id: str = ""
    task_id: str = ""
    runner: str = ""
    model: str = ""
    budget_profile: str = ""
    comparison_mode: str = "non_strict"
    setting_warnings: list[str] = field(default_factory=list)
    success_visible: bool = False
    success_hidden: bool = False
    status: str = "harness_error"
    wall_time_sec: float = 0.0
    model_calls: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    shell_commands: int | None = None
    file_reads: int | None = None
    file_writes: int | None = None
    files_touched: list[str] = field(default_factory=list)
    lines_added: int = 0
    lines_deleted: int = 0
    patch_size_lines: int = 0
    first_relevant_file_seen_at_sec: float | None = None
    first_patch_at_sec: float | None = None
    verification_attempts: int | None = None
    last_action_was_verification: bool | None = None
    expected_file_touched: bool = False
    decoy_file_touched: bool = False
    tests_modified: bool = False
    forbidden_file_modified: bool = False
    failure_mode: str | None = None
    failure_mode_confidence: float | None = None
    budget_exceeded: bool = False
    runner_crashed: bool = False
    timed_out: bool = False
    telemetry_completeness: str = "partial"
    missing_telemetry: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
