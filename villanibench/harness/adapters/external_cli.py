from __future__ import annotations

import subprocess
from pathlib import Path

from .base import AdapterRunResult, RunnerAdapter, now_iso


class ExternalCliAdapter(RunnerAdapter):
    def __init__(self, name: str, default_template: str):
        self.name = name
        self.default_template = default_template

    def resolve_template(self, config: dict) -> str:
        return str(config.get("command_template") or self.default_template)

    def _comparison_mode_and_warnings(self, template: str, config: dict) -> tuple[str, list[str]]:
        warnings: list[str] = []
        model_used = "{model}" in template
        base_url_provided = bool(config.get("base_url"))
        base_url_used = "{base_url}" in template
        strict = model_used and (base_url_used or not base_url_provided)
        if base_url_provided and not base_url_used:
            warnings.append("base_url_not_used_by_template")
        return ("strict" if strict else "non_strict"), warnings

    def render_command(self, template: str, **kwargs: str) -> str:
        return template.format(**kwargs)

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        template = self.resolve_template(config)
        prompt_file = (sandbox_dir / "prompt.txt").resolve()
        prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
        cwd = (sandbox_dir / "repo").resolve()
        comparison_mode, warnings = self._comparison_mode_and_warnings(template, config)
        command = self.render_command(
            template,
            prompt_file=str(prompt_file),
            prompt_text=prompt_text,
            cwd=str(cwd),
            model=str(config.get("model", "")),
            base_url=str(config.get("base_url", "")),
            api_key=str(config.get("api_key", "")),
            output_dir=str(output_dir.resolve()),
            visible_test_command=str(task.visible_test_command),
        )
        started = now_iso()
        timed_out = False
        runner_crashed = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            try:
                completed = subprocess.run(
                    command,
                    cwd=cwd,
                    shell=True,
                    stdout=out,
                    stderr=err,
                    timeout=budget.wall_time_sec,
                    text=True,
                )
                exit_code = completed.returncode
                runner_crashed = completed.returncode != 0
            except subprocess.TimeoutExpired:
                timed_out = True
                runner_crashed = False
                exit_code = 124
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
            raw_command=command,
            comparison_mode=comparison_mode,
            setting_warnings=warnings,
        )
