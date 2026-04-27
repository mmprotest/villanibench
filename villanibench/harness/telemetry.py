from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Telemetry:
    model_calls: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    shell_commands: int | None = None
    file_reads: int | None = None
    file_writes: int | None = None
    telemetry_completeness: str = "partial"
    missing_telemetry: list[str] = field(default_factory=lambda: [
        "model_calls",
        "tokens_input",
        "tokens_output",
        "shell_commands",
        "file_reads",
        "file_writes",
    ])
