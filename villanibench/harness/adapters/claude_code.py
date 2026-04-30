from __future__ import annotations

import os
import shlex
from pathlib import Path

from villanibench.harness.process import run_command_tree_argv

from .external_cli import ExternalCliAdapter
from .base import AdapterRunResult, now_iso


DEFAULT_TEMPLATE = "claude -p --dangerously-skip-permissions --model {model}"


class ClaudeCodeAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="claude_code", default_template=DEFAULT_TEMPLATE)

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        command_path = output_dir / "runner_command.txt"
        prompt_file = (sandbox_dir / "prompt.txt").resolve()
        prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
        cwd = (sandbox_dir / "repo").resolve()

        model = str(config.get("model", ""))
        argv = ["claude", "-p", "--dangerously-skip-permissions", "--model", model]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        if config.get("base_url"):
            env["ANTHROPIC_BASE_URL"] = str(config["base_url"])
        if config.get("api_key"):
            token = str(config["api_key"])
            env["ANTHROPIC_AUTH_TOKEN"] = token
            env["ANTHROPIC_API_KEY"] = token

        display = " ".join(shlex.quote(p) for p in argv)
        display += "\n# stdin: prompt.txt"
        if config.get("base_url"):
            display += "\nANTHROPIC_BASE_URL=<set>"
        if config.get("api_key"):
            display += "\nANTHROPIC_AUTH_TOKEN=<redacted>"
            display += "\nANTHROPIC_API_KEY=<redacted>"
        command_path.write_text(display + "\n", encoding="utf-8")

        started = now_iso()
        timed_out = False
        runner_crashed = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            try:
                completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, stdin_text=prompt_text)
                out.write(completed.stdout)
                err.write(completed.stderr)
                timed_out = completed.timed_out
                exit_code = completed.exit_code
                runner_crashed = completed.exit_code != 0 and not completed.timed_out
            except Exception as exc:
                err.write(f"Adapter execution error: {exc}\n")
                runner_crashed = True
                exit_code = 1
        ended = now_iso()
        return AdapterRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at=started,
            ended_at=ended,
            timed_out=timed_out,
            runner_crashed=runner_crashed,
            raw_command=display,
            comparison_mode="strict",
            control_kind=None,
            setting_warnings=[],
            notes=None,
        )
