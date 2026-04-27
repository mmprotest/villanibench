from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from villanibench.harness.telemetry import Telemetry


@dataclass
class AdapterRunResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    started_at: str
    ended_at: str
    timed_out: bool
    runner_crashed: bool
    raw_command: str
    comparison_mode: str
    control_kind: str | None = None
    setting_warnings: list[str] = field(default_factory=list)


class RunnerAdapter:
    name: str = "base"

    def prepare(self, task, sandbox_dir: Path, config: dict) -> None:
        return None

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        raise NotImplementedError

    def collect_telemetry(self, sandbox_dir: Path) -> Telemetry:
        return Telemetry()

    def cleanup(self, sandbox_dir: Path) -> None:
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
