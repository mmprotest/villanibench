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
    Write user-level Qwen settings into an isolated HOME.

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


def _string_attr(obj: Any, name: str) -> str:
    value = getattr(obj, name, None)
    if value is None:
        return ""
    if callable(value):
        try:
            value = value()
        except TypeError:
            return ""
    if value is None:
        return ""
    return str(value).strip()


def _read_first_existing(paths: list[Path]) -> str:
    for path in paths:
        try:
            if path.exists() and path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except OSError:
            continue
    return ""


def _resolve_task_text(task: Any, sandbox_dir: Path) -> str:
    """
    Resolve the real benchmark instruction.

    Some VillaniBench tasks do not expose the prompt as `task.prompt`; the prompt
    may exist as sandbox/prompt.txt.
    """
    attr_candidates = [
        "prompt",
        "task_prompt",
        "instruction",
        "instructions",
        "description",
        "task",
    ]
    for attr in attr_candidates:
        text = _string_attr(task, attr)
        if text:
            return text

    path_attr_candidates = [
        "prompt_path",
        "prompt_file",
        "instructions_path",
        "instruction_path",
        "task_path",
    ]
    path_candidates: list[Path] = []
    for attr in path_attr_candidates:
        raw = getattr(task, attr, None)
        if raw:
            candidate = Path(raw)
            if not candidate.is_absolute():
                path_candidates.append((sandbox_dir / candidate).resolve())
                path_candidates.append((sandbox_dir / "repo" / candidate).resolve())
            else:
                path_candidates.append(candidate)

    path_candidates.extend(
        [
            sandbox_dir / "prompt.txt",
            sandbox_dir / "task.txt",
            sandbox_dir / "instructions.txt",
            sandbox_dir / "repo" / "prompt.txt",
            sandbox_dir / "repo" / "task.txt",
            sandbox_dir / "repo" / "instructions.txt",
        ]
    )

    return _read_first_existing(path_candidates)


def _resolve_visible_verification(task: Any, sandbox_dir: Path) -> str:
    attr_candidates = [
        "visible_test_command",
        "visible_verification",
        "visible_verification_command",
        "verification_command",
        "test_command",
    ]
    for attr in attr_candidates:
        text = _string_attr(task, attr)
        if text:
            return text

    return _read_first_existing(
        [
            sandbox_dir / "visible_test_command.txt",
            sandbox_dir / "verification.txt",
            sandbox_dir / "repo" / "visible_test_command.txt",
            sandbox_dir / "repo" / "verification.txt",
        ]
    )


def _repo_file_overview(repo_dir: Path, *, max_files: int = 80) -> str:
    """
    Give the model a cheap map of the repo.

    This is not a substitute for Qwen's file tools, but it reduces the chance
    that small/local models answer with "ready" instead of starting.
    """
    ignored_dirs = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".qwen",
        ".venv",
        "venv",
        "node_modules",
    }
    files: list[str] = []
    try:
        for path in sorted(repo_dir.rglob("*")):
            if len(files) >= max_files:
                break
            rel = path.relative_to(repo_dir)
            parts = set(rel.parts)
            if parts & ignored_dirs:
                continue
            if path.is_file():
                files.append(str(rel).replace("\\", "/"))
    except OSError:
        return "(repo file overview unavailable)"

    if not files:
        return "(no files found)"
    return "\n".join(f"- {name}" for name in files)


def _build_task_payload(task: Any, sandbox_dir: Path, repo_dir: Path) -> str:
    task_text = _resolve_task_text(task, sandbox_dir)
    if not task_text:
        raise ValueError(
            "Qwen CLI adapter resolved an empty task prompt. "
            "Expected a non-empty task prompt on the task object or in sandbox/prompt.txt."
        )

    verify = _resolve_visible_verification(task, sandbox_dir)
    verify_section = verify if verify else "(not provided)"

    return (
        "BENCHMARK CODING TASK\n\n"
        "You are already inside the repository that must be modified.\n"
        "Do the task now. Do not acknowledge readiness. Do not ask what to do.\n"
        "Inspect the files, edit the correct source file, run the visible verification, then stop.\n\n"
        "Rules:\n"
        "- Work only inside the current repository.\n"
        "- Make the smallest correct code change.\n"
        "- Do not edit benchmark metadata unless explicitly required.\n"
        "- Do not edit tests unless the task explicitly asks you to.\n"
        "- Do not create unrelated files.\n"
        "- If tests fail, inspect the failure and fix the implementation.\n"
        "- Finish only after making the repository change or determining that no change is possible.\n\n"
        "Task:\n"
        f"{task_text}\n\n"
        "Visible verification command:\n"
        f"{verify_section}\n\n"
        "Repository file overview:\n"
        f"{_repo_file_overview(repo_dir)}\n"
    )


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

            # Keep Qwen configuration outside the benchmark repo so adapter-owned
            # files cannot be mistaken for a task solution.
            _remove_repo_qwen_config_if_adapter_owned(cwd)
            qwen_home = (output_dir / "qwen_home").resolve()
            settings_path = _write_qwen_settings(qwen_home=qwen_home, model=model, base_url=base_url)
            redacted_settings_path.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")

            task_payload = _build_task_payload(task, sandbox_dir, cwd)
            prompt_path.write_text(task_payload, encoding="utf-8")

            # Use a short imperative -p prompt and send the full task payload via
            # stdin. This avoids Windows npm .CMD/newline argument weirdness and
            # avoids the model treating a long setup-style prompt as "context only".
            prompt_arg = (
                "Complete the benchmark coding task provided on stdin. "
                "Start now: inspect files, edit the repository, run the visible verification, "
                "and do not reply that you are ready."
            )
            argv = [
                exe,
                "-p",
                prompt_arg,
                "--output-format",
                "json",
                "--approval-mode",
                "yolo",
                "--model",
                model,
            ]

            env = os.environ.copy()
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

            completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, stdin_text=task_payload)
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            result_path.write_text(json.dumps(parse_qwen_output(completed.stdout), indent=2) + "\n", encoding="utf-8")

            command_artifact = {
                "argv": [
                    exe,
                    "-p",
                    prompt_arg,
                    "--output-format",
                    "json",
                    "--approval-mode",
                    "yolo",
                    "--model",
                    model,
                ],
                "stdin_prompt_path": str(prompt_path),
                "cwd": str(cwd),
                "qwen_executable": exe,
                "qwen_home": str(qwen_home),
                "settings_path": str(settings_path),
                "model": model,
                "base_url": base_url,
                "timeout": budget.wall_time_sec,
                "exit_code": completed.exit_code,
                "timed_out": completed.timed_out,
                "wall_time_sec": completed.wall_time_sec,
            }
            command_path.write_text(json.dumps(command_artifact, indent=2) + "\n", encoding="utf-8")

            ended = now_iso()
            raw_command = " ".join(
                shlex.quote(p)
                for p in [
                    exe,
                    "-p",
                    prompt_arg,
                    "--output-format",
                    "json",
                    "--approval-mode",
                    "yolo",
                    "--model",
                    model,
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
