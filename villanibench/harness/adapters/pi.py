from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from villanibench.harness.process import run_command_tree_argv

from .base import AdapterRunResult, RunnerAdapter, now_iso

PI_PROVIDER_ID = "villani-local"
PI_API_KEY_ENV = "VILLANI_PI_API_KEY"


def _normalise_base_url(base_url: Any) -> str | None:
    if base_url is None:
        return None
    value = str(base_url).strip()
    if not value:
        return None
    if not value.rstrip("/").endswith("/v1"):
        value = value.rstrip("/") + "/v1"
    return value


def _raw_model_id(model: Any) -> str:
    value = str(model).strip()
    prefix = "villani-local/"
    if value.startswith(prefix):
        value = value[len(prefix) :]
    if not value:
        raise ValueError("Pi model cannot be empty")
    return value


def _resolve_pi_executable(config: dict) -> str:
    for key in ("command", "executable", "pi_path"):
        value = str(config.get(key, "")).strip()
        if value:
            return value

    for candidate in ("pi", "pi.cmd", "pi.exe", "pi.bat"):
        exe = shutil.which(candidate)
        if exe:
            return exe

    raise RuntimeError("Pi executable not found. Set adapter config 'pi_path' (or 'command'/'executable') or install pi on PATH.")


def _write_models_json(*, pi_root: Path, model: str, base_url: str) -> Path:
    models_dir = pi_root / "agent"
    models_dir.mkdir(parents=True, exist_ok=True)
    models_path = models_dir / "models.json"

    raw_model = _raw_model_id(model)
    config = {
        "providers": {
            PI_PROVIDER_ID: {
                "baseUrl": base_url,
                "api": "openai-completions",
                "apiKey": PI_API_KEY_ENV,
                "models": [
                    {
                        "id": raw_model,
                        "name": raw_model,
                        "reasoning": False,
                        "input": ["text"],
                        "contextWindow": 128000,
                        "maxTokens": 16384,
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0,
                        },
                        "compat": {
                            "supportsDeveloperRole": False,
                            "supportsReasoningEffort": False,
                            "supportsUsageInStreaming": False,
                        },
                    }
                ],
            }
        }
    }

    models_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return models_path


class PiAdapter(RunnerAdapter):
    name = "pi"

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        command_path = output_dir / "runner_command.txt"

        prompt_file = (sandbox_dir / "prompt.txt").resolve()
        prompt_text = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
        cwd = (sandbox_dir / "repo").resolve()

        try:
            exe = _resolve_pi_executable(config)
            model = str(config.get("model", "")).strip()
            raw_model = _raw_model_id(model)
            base_url = _normalise_base_url(config.get("base_url"))

            pi_root = (sandbox_dir / ".pi-agent").resolve()
            pi_sessions = (sandbox_dir / ".pi-sessions").resolve()
            pi_root.mkdir(parents=True, exist_ok=True)
            pi_sessions.mkdir(parents=True, exist_ok=True)

            argv = [exe, "--mode", "json", "--no-session"]
            if base_url is not None:
                _write_models_json(pi_root=pi_root, model=raw_model, base_url=base_url)
                argv += ["--provider", PI_PROVIDER_ID, "--model", raw_model, prompt_text]
            else:
                argv += ["--model", model, prompt_text]

            env = os.environ.copy()
            env.update({str(k): str(v) for k, v in (config.get("env") or {}).items()})
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["PI_CODING_AGENT_DIR"] = str(pi_root)
            env["PI_CODING_AGENT_SESSION_DIR"] = str(pi_sessions)
            env["PI_OFFLINE"] = "1"
            env["PI_SKIP_VERSION_CHECK"] = "1"
            env["PI_TELEMETRY"] = "0"
            env[PI_API_KEY_ENV] = str(config.get("api_key") or "dummy")

            display_argv = argv[:-1] + ["<prompt_text>"]
            display = " ".join(shlex.quote(x) for x in display_argv)
            if base_url is not None:
                display += "\nVILLANI_PI_API_KEY=<redacted>"
            command_path.write_text(display + "\n", encoding="utf-8")

            started = now_iso()
            with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
                completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, stdin_text=None)
                out.write(completed.stdout)
                err.write(completed.stderr)

            ended = now_iso()
            return AdapterRunResult(
                exit_code=completed.exit_code,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started,
                ended_at=ended,
                timed_out=completed.timed_out,
                runner_crashed=completed.exit_code != 0 and not completed.timed_out,
                raw_command=display,
                comparison_mode="strict",
                control_kind=None,
                setting_warnings=[],
                notes=None,
            )
        except Exception as exc:
            stderr_path.write_text(f"Adapter execution error: {exc}\n", encoding="utf-8")
            stdout_path.write_text("", encoding="utf-8")
            return AdapterRunResult(
                exit_code=1,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=now_iso(),
                ended_at=now_iso(),
                timed_out=False,
                runner_crashed=True,
                raw_command="pi",
                comparison_mode="strict",
                control_kind=None,
                setting_warnings=[],
                notes=None,
            )
