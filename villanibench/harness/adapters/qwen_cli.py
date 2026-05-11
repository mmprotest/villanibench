from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from villanibench.harness.os_sandbox_user import sandbox_env
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

        override_path = Path(override)
        if override_path.exists():
            return str(override_path)

    exe = shutil.which("qwen")
    if exe:
        return exe

    raise RuntimeError(
        "Qwen Code CLI executable not found. Install it with:\n"
        "npm install -g @qwen-code/qwen-code@latest\n"
        "or set QWEN_CLI_BIN."
    )


def _write_qwen_settings(*, qwen_home: Path, model: str, base_url: str) -> Path:
    """
    Write Qwen settings into an isolated HOME.

    Do not write `.qwen/settings.json` inside the benchmark repo. If settings
    live under sandbox/repo, VillaniBench can accidentally count adapter-owned
    config as the agent patch.
    """
    settings_dir = qwen_home / ".qwen"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"

    settings = {
        "$version": 3,
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
        "model": {
            "name": model,
            "generationConfig": {
                "samplingParams": {"temperature": 0.0},
            },
        },
        "output": {"format": "json"},
        "permissions": {
            "defaultMode": "yolo",
            "confirmShellCommands": False,
            "confirmFileEdits": False,
        },
        "privacy": {"usageStatisticsEnabled": False},
        "telemetry": {"enabled": False},
    }

    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path


def parse_qwen_output(stdout: str) -> dict[str, Any]:
    """
    Parse both documented JSON-array output and stream-json/NDJSON output.

    Some installed Qwen versions still emit plain text even when json output is
    requested. That should be recorded, not treated as an adapter crash.
    """
    text = stdout.strip()
    if not text:
        return {"empty_stdout": True}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        messages: list[Any] = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                messages = []
                break

        if messages:
            result = None
            for item in reversed(messages):
                if isinstance(item, dict) and item.get("type") == "result":
                    result = item
                    break

            return {"result": result, "messages": messages}

        return {"json_parse_error": str(exc), "raw_stdout_tail": stdout[-20000:]}

    result = None
    if isinstance(payload, list):
        for item in reversed(payload):
            if isinstance(item, dict) and item.get("type") == "result":
                result = item
                break

    return {"result": result, "messages": payload}


def _remove_repo_qwen_config_if_adapter_owned(repo_dir: Path) -> None:
    """
    Clean up stale adapter-owned Qwen config from earlier broken runs.

    This deliberately removes only the known adapter-created files. It does not
    delete arbitrary project files.
    """
    qwen_dir = repo_dir / ".qwen"

    for name in ("settings.json", "settings.json.orig"):
        path = qwen_dir / name
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    try:
        qwen_dir.rmdir()
    except OSError:
        pass


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
        prompt_path = output_dir / "qwen_cli_prompt.txt"

        sandbox_dir = sandbox_dir.resolve()
        cwd = (sandbox_dir / "repo").resolve()

        model = str(config.get("model", "")).strip()
        base_url = _normalise_base_url(config.get("base_url"))

        started = now_iso()
        raw_command = "qwen"

        try:
            exe = _resolve_qwen_executable()

            if not model:
                raise ValueError("Qwen CLI adapter requires model")

            if not base_url:
                raise ValueError("Qwen CLI adapter requires base_url")

            prompt_src = sandbox_dir / "prompt.txt"
            if not prompt_src.exists():
                raise FileNotFoundError(f"Missing benchmark prompt file: {prompt_src}")

            # Fairness rule:
            # Pass the benchmark prompt verbatim. Do not append adapter instructions,
            # expected files, visible verification, rules, repo maps, or oracle metadata.
            prompt_text = prompt_src.read_text(encoding="utf-8")
            prompt_path.write_text(prompt_text, encoding="utf-8")

            # Keep Qwen configuration outside the benchmark repo so adapter-owned
            # files cannot be mistaken for a task solution.
            _remove_repo_qwen_config_if_adapter_owned(cwd)
            qwen_home = (output_dir / "qwen_home").resolve()
            settings_path = _write_qwen_settings(
                qwen_home=qwen_home,
                model=model,
                base_url=base_url,
            )
            redacted_settings_path.write_text(
                settings_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            # Put approval mode before -p and use the equals form. Some Qwen CLI
            # versions appear to ignore `--approval-mode yolo` when it appears
            # after the prompt argument.
            argv = [
                exe,
                "--approval-mode=yolo",
                "--output-format",
                "json",
                "--model",
                model,
                "-p",
                prompt_text,
            ]

            env = sandbox_env(os.environ.copy(), Path(config["task_output_dir"]))
            api_key = str(config.get("api_key") or "dummy")

            env[QWEN_API_KEY_ENV] = api_key
            env["OPENAI_API_KEY"] = api_key
            env["OPENAI_BASE_URL"] = base_url
            env["OPENAI_MODEL"] = model
            env["NO_COLOR"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["QWEN_SANDBOX"] = "false"

            # Force Qwen to read isolated user settings rather than the developer's
            # global ~/.qwen/settings.json.
            env["HOME"] = str(qwen_home)
            env["USERPROFILE"] = str(qwen_home)
            env["XDG_CONFIG_HOME"] = str(qwen_home)

            completed = run_command_tree_argv(
                argv,
                cwd,
                budget.wall_time_sec,
                env=env,
                stdin_text=None,
                sandbox_identity=config.get("sandbox_identity"),
            )

            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            result_path.write_text(
                json.dumps(parse_qwen_output(completed.stdout), indent=2) + "\n",
                encoding="utf-8",
            )

            command_artifact = {
                "argv": [
                    exe,
                    "--approval-mode=yolo",
                    "--output-format",
                    "json",
                    "--model",
                    model,
                    "-p",
                    "<prompt_text>",
                ],
                "cwd": str(cwd),
                "qwen_executable": exe,
                "qwen_home": str(qwen_home),
                "settings_path": str(settings_path),
                "prompt_file": str(prompt_path),
                "prompt_is_verbatim_benchmark_prompt": True,
                "uses_oracle_expected_files": False,
                "passes_file_hints": False,
                "passes_visible_verification": False,
                "passes_repo_overview": False,
                "model": model,
                "base_url": base_url,
                "timeout": budget.wall_time_sec,
                "exit_code": completed.exit_code,
                "timed_out": completed.timed_out,
                "wall_time_sec": completed.wall_time_sec,
            }
            command_path.write_text(
                json.dumps(command_artifact, indent=2) + "\n",
                encoding="utf-8",
            )

            ended = now_iso()

            raw_command = " ".join(
                shlex.quote(p)
                for p in [
                    exe,
                    "--approval-mode=yolo",
                    "--output-format",
                    "json",
                    "--model",
                    model,
                    "-p",
                    "<prompt_text>",
                ]
            )

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
            stderr_path.write_text(
                f"Adapter execution error: {type(exc).__name__}: {exc}\n",
                encoding="utf-8",
            )
            stdout_path.write_text("", encoding="utf-8")
            result_path.write_text(
                json.dumps(
                    {
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "prompt_is_verbatim_benchmark_prompt": True,
                        "uses_oracle_expected_files": False,
                        "passes_file_hints": False,
                        "passes_visible_verification": False,
                        "passes_repo_overview": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            ended = now_iso()

            return AdapterRunResult(
                exit_code=1,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started,
                ended_at=ended,
                timed_out=False,
                runner_crashed=True,
                raw_command=raw_command,
                comparison_mode="strict",
                control_kind=None,
                setting_warnings=[],
                notes=str(exc),
            )