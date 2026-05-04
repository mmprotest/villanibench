from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from villanibench.harness.process import run_command_tree_argv

from .base import AdapterRunResult, RunnerAdapter, now_iso

QWEN_API_KEY_ENV = "VILLANIBENCH_QWEN_API_KEY"


def _normalise_base_url(base_url: Any) -> str | None:
    if base_url is None:
        return None
    value = str(base_url).strip()
    if not value:
        return None
    if not value.rstrip("/").endswith("/v1"):
        value = value.rstrip("/") + "/v1"
    return value


def _resolve_qwen_executable() -> str:
    override = str(os.environ.get("QWEN_CLI_BIN", "")).strip()
    if override:
        exe = shutil.which(override)
        if exe:
            return exe
    exe = shutil.which("qwen")
    if exe:
        return exe
    raise RuntimeError(
        "Qwen Code CLI executable not found. Install it with:\n"
        "npm install -g @qwen-code/qwen-code@latest\n"
        "or set QWEN_CLI_BIN."
    )


def _write_qwen_settings(*, cwd: Path, model: str, base_url: str) -> Path:
    settings_dir = cwd / ".qwen"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    settings = {
        "modelProviders": {
            "openai": [
                {
                    "id": model,
                    "name": model,
                    "baseUrl": base_url,
                    "envKey": QWEN_API_KEY_ENV,
                    "generationConfig": {
                        "timeout": 300000,
                        "maxRetries": 0,
                        "samplingParams": {"temperature": 0.0},
                    },
                }
            ]
        },
        "security": {"auth": {"selectedType": "openai"}},
        "model": {"name": model},
        "tools": {"approvalMode": "yolo"},
        "telemetry": {"enabled": False},
    }
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path


def parse_qwen_output(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {"json_parse_error": str(exc), "raw_stdout_tail": stdout[-20000:]}

    result = None
    if isinstance(payload, list):
        for item in reversed(payload):
            if isinstance(item, dict) and item.get("type") == "result":
                result = item
                break

    return {"result": result, "messages": payload}


def _build_prompt(task) -> str:
    task_text = getattr(task, "prompt", None) or ""
    verify = getattr(task, "visible_test_command", None) or ""
    verify_section = verify if verify else "(not provided)"
    return (
        "You are running inside a benchmark task repository.\n\n"
        "Your job is to modify the repository so the task passes its visible verification.\n\n"
        "Rules:\n"
        "- Work only inside the current repository.\n"
        "- Read the task instructions carefully.\n"
        "- Make the smallest correct code change.\n"
        "- Do not edit benchmark metadata unless explicitly required.\n"
        "- Do not create unrelated files.\n"
        "- Run the relevant tests or verification commands before finishing.\n"
        "- When done, stop.\n\n"
        f"Task:\n{task_text}\n\n"
        f"Visible verification:\n{verify_section}\n"
    )


class QwenCliAdapter(RunnerAdapter):
    name = "qwen-cli"

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = output_dir / "qwen_cli_stdout.txt"
        stderr_path = output_dir / "qwen_cli_stderr.txt"
        result_path = output_dir / "qwen_cli_result.json"
        command_path = output_dir / "qwen_cli_command.json"
        redacted_settings_path = output_dir / "qwen_settings_redacted.json"

        cwd = (sandbox_dir / "repo").resolve()
        model = str(config.get("model", "")).strip()
        base_url = _normalise_base_url(config.get("base_url"))

        started = now_iso()
        try:
            exe = _resolve_qwen_executable()
            if not model:
                raise ValueError("Qwen CLI adapter requires model")
            if not base_url:
                raise ValueError("Qwen CLI adapter requires base_url")

            settings_path = _write_qwen_settings(cwd=cwd, model=model, base_url=base_url)
            redacted_settings_path.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")

            prompt = _build_prompt(task)
            argv = [
                exe,
                "--prompt",
                prompt,
                "--output-format",
                "json",
                "--approval-mode",
                "yolo",
                "--model",
                model,
            ]

            env = os.environ.copy()
            env[QWEN_API_KEY_ENV] = str(config.get("api_key") or "dummy")
            env["NO_COLOR"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, stdin_text=None)
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            result_path.write_text(json.dumps(parse_qwen_output(completed.stdout), indent=2) + "\n", encoding="utf-8")

            command_artifact = {
                "argv": argv,
                "cwd": str(cwd),
                "qwen_executable": exe,
                "model": model,
                "base_url": base_url,
                "timeout": budget.wall_time_sec,
                "exit_code": completed.exit_code,
                "timed_out": completed.timed_out,
                "wall_time_sec": completed.wall_time_sec,
            }
            command_path.write_text(json.dumps(command_artifact, indent=2) + "\n", encoding="utf-8")

            ended = now_iso()
            raw_command = " ".join(shlex.quote(p) for p in [exe, "--prompt", "<prompt>", "--output-format", "json", "--approval-mode", "yolo", "--model", model])
            return AdapterRunResult(
                exit_code=completed.exit_code,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started,
                ended_at=ended,
                timed_out=completed.timed_out,
                runner_crashed=completed.exit_code != 0 and not completed.timed_out,
                raw_command=raw_command,
                comparison_mode="strict",
                control_kind=None,
                setting_warnings=[],
                notes=None,
            )
        except Exception as exc:
            stderr_path.write_text(f"Adapter execution error: {exc}\n", encoding="utf-8")
            stdout_path.write_text("", encoding="utf-8")
            result_path.write_text(json.dumps({"error": str(exc)}, indent=2) + "\n", encoding="utf-8")
            ended = now_iso()
            return AdapterRunResult(
                exit_code=1,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started,
                ended_at=ended,
                timed_out=False,
                runner_crashed=True,
                raw_command="qwen",
                comparison_mode="strict",
            )
