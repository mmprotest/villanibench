from __future__ import annotations

import subprocess
from pathlib import Path

from .base import AdapterRunResult, RunnerAdapter, now_iso


class MinimalReactControlAdapter(RunnerAdapter):
    name = "minimal_react_control"

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        started = now_iso()
        cmd = task.visible_test_command
        timed_out = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=sandbox_dir,
                    shell=True,
                    stdout=out,
                    stderr=err,
                    timeout=budget.wall_time_sec,
                    text=True,
                )
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = 124
        ended = now_iso()
        return AdapterRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at=started,
            ended_at=ended,
            timed_out=timed_out,
            runner_crashed=False,
            raw_command=cmd,
            comparison_mode="non_strict",
            setting_warnings=["minimal_react_control_placeholder_no_model_calls"],
        )
