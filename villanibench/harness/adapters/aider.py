from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from villanibench.harness.process import run_command_tree_argv

from .base import AdapterRunResult, RunnerAdapter, now_iso


@dataclass(frozen=True)
class AiderModelConfig:
    provider: str
    model: str
    env: dict[str, str]
    cli_args: list[str]


def _strip_provider_prefix(model: str) -> str:
    value = str(model or "").strip()
    if "/" not in value:
        return value
    return value.split("/", 1)[1].strip()


def _normalize_provider(config: dict[str, Any], model: str) -> str:
    raw = (
        config.get("aider_provider")
        or config.get("provider")
        or config.get("backend_provider")
        or ""
    )
    provider = str(raw).strip().lower()

    if provider:
        return provider

    lowered = model.lower().strip()

    if lowered.startswith("lm_studio/") or lowered.startswith("lm-studio/"):
        return "lm_studio"
    if lowered.startswith("openai/"):
        return "openai"
    if lowered.startswith("openrouter/"):
        return "openrouter"
    if lowered.startswith("anthropic/"):
        return "anthropic"

    return "openai"


def build_aider_model_config(config: dict[str, Any]) -> AiderModelConfig:
    raw_model = str(config.get("model") or "").strip()
    if not raw_model:
        raise ValueError("Aider adapter requires config['model']")

    provider = _normalize_provider(config, raw_model)
    base_url = str(config.get("base_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip() or "dummy"

    env: dict[str, str] = {}
    cli_args: list[str] = []

    if provider in {"lm_studio", "lm-studio", "lmstudio"}:
        model_name = _strip_provider_prefix(raw_model)
        if not model_name:
            raise ValueError("Aider LM Studio provider requires a model name")
        if not base_url:
            raise ValueError("Aider LM Studio provider requires config['base_url']")

        provider = "lm_studio"
        model = f"lm_studio/{model_name}"
        env["LM_STUDIO_API_BASE"] = base_url
        env["LM_STUDIO_API_KEY"] = api_key or "dummy-api-key"

    elif provider in {"openai", "openai_compatible", "openai-compatible"}:
        model = raw_model if raw_model.startswith("openai/") else f"openai/{raw_model}"

        if not base_url:
            raise ValueError("Aider OpenAI-compatible provider requires config['base_url']")

        env["OPENAI_API_BASE"] = base_url
        env["OPENAI_API_KEY"] = api_key
        cli_args.extend(["--openai-api-base", base_url, "--openai-api-key", api_key])

    elif provider == "openrouter":
        model_name = _strip_provider_prefix(raw_model)
        if not model_name:
            raise ValueError("Aider OpenRouter provider requires a model name")

        model = f"openrouter/{model_name}"
        env["OPENROUTER_API_KEY"] = api_key

        if base_url:
            env["OPENAI_API_BASE"] = base_url
            env["OPENAI_API_KEY"] = api_key
            cli_args.extend(["--openai-api-base", base_url, "--openai-api-key", api_key])

    elif provider == "anthropic":
        model = raw_model if raw_model.startswith("anthropic/") else f"anthropic/{raw_model}"
        env["ANTHROPIC_API_KEY"] = api_key

    else:
        model = raw_model

        if base_url:
            env["OPENAI_API_BASE"] = base_url
            env["OPENAI_API_KEY"] = api_key
            cli_args.extend(["--openai-api-base", base_url, "--openai-api-key", api_key])

    return AiderModelConfig(
        provider=provider,
        model=model,
        env=env,
        cli_args=cli_args,
    )


def _write_hermetic_aider_files(output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = (output_dir / "aider.conf.yml").resolve()
    env_path = (output_dir / "aider.env").resolve()
    aiderignore_path = (output_dir / "aiderignore").resolve()

    config_path.write_text(
        "\n".join(
            [
                "analytics-disable: true",
                "check-update: false",
                "show-release-notes: false",
                "auto-commits: false",
                "dirty-commits: false",
                "attribute-author: false",
                "attribute-committer: false",
                "attribute-commit-message-author: false",
                "attribute-commit-message-committer: false",
                "attribute-co-authored-by: false",
                "auto-lint: false",
                "auto-test: false",
                "stream: false",
                "pretty: false",
                "detect-urls: false",
                "suggest-shell-commands: false",
                "fancy-input: false",
                "multiline: false",
                "notifications: false",
                "watch-files: false",
                "gui: false",
                "browser: false",
                "show-model-warnings: false",
                "check-model-accepts-settings: false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env_path.write_text("", encoding="utf-8")
    aiderignore_path.write_text("", encoding="utf-8")

    return config_path, env_path, aiderignore_path


def _write_aider_model_metadata(output_dir: Path, model: str, provider: str) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    path = (output_dir / "aider.model.metadata.json").resolve()

    litellm_provider = "openai"
    if provider == "openrouter":
        litellm_provider = "openrouter"
    elif provider == "anthropic":
        litellm_provider = "anthropic"

    payload = {
        model: {
            "max_tokens": 65536,
            "max_input_tokens": 65536,
            "max_output_tokens": 8192,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "litellm_provider": litellm_provider,
            "mode": "chat",
        }
    }

    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _build_redacted_argv(argv: list[str], redacted_values: set[str]) -> list[str]:
    redacted_values = {value for value in redacted_values if value}
    return [
        "<redacted>" if str(item) in redacted_values else str(item)
        for item in argv
    ]


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "bench",
            "GIT_AUTHOR_EMAIL": "bench@example.com",
            "GIT_COMMITTER_NAME": "bench",
            "GIT_COMMITTER_EMAIL": "bench@example.com",
        }
    )
    return env


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=_git_env(),
    )


def _ensure_isolated_git_repo(cwd: Path) -> bool:
    """
    Ensure Aider sees the benchmark sandbox as its repo, not the parent
    VillaniBench repo.

    Returns True if this function created a temporary repo, False if the
    sandbox already had its own .git directory.
    """
    cwd = cwd.resolve()

    if (cwd / ".git").exists():
        return False

    _run_git(["init"], cwd)
    _run_git(["config", "user.name", "bench"], cwd)
    _run_git(["config", "user.email", "bench@example.com"], cwd)
    _run_git(["add", "-A"], cwd)

    try:
        _run_git(["commit", "-m", "benchmark baseline"], cwd)
    except subprocess.CalledProcessError:
        # Empty repos are unusual for these tasks, but do not crash just because
        # there was nothing to commit.
        pass

    return True


class AiderAdapter(RunnerAdapter):
    name = "aider"

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        sandbox_dir = sandbox_dir.resolve()
        cwd = (sandbox_dir / "repo").resolve()

        stdout_path = (output_dir / "aider_stdout.txt").resolve()
        stderr_path = (output_dir / "aider_stderr.txt").resolve()
        prompt_path = (output_dir / "aider_prompt.txt").resolve()
        command_path = (output_dir / "aider_command.json").resolve()
        result_path = (output_dir / "aider_result.json").resolve()

        started = now_iso()
        raw_command = "aider"

        try:
            exe = shutil.which("aider") or shutil.which("aider.cmd") or "aider"

            model_config = build_aider_model_config(config)
            config_path, env_file_path, aiderignore_path = _write_hermetic_aider_files(output_dir)
            model_metadata_path = _write_aider_model_metadata(
                output_dir,
                model_config.model,
                model_config.provider,
            )

            prompt_src = sandbox_dir / "prompt.txt"
            if not prompt_src.exists():
                raise FileNotFoundError(f"Missing benchmark prompt file: {prompt_src}")

            # Fairness rule:
            # Pass the benchmark prompt verbatim. Do not append adapter instructions,
            # expected files, visible verification, rules, or oracle metadata.
            prompt_text = prompt_src.read_text(encoding="utf-8")
            prompt_path.write_text(prompt_text, encoding="utf-8")

            created_git_repo = _ensure_isolated_git_repo(cwd)

            argv = [
                exe,
                "--config",
                str(config_path),
                "--env-file",
                str(env_file_path),
                "--aiderignore",
                str(aiderignore_path),
                "--model",
                model_config.model,
                "--model-metadata-file",
                str(model_metadata_path),
                *model_config.cli_args,
                "--message-file",
                str(prompt_path),

                # Non-interactive benchmark mode.
                "--yes-always",
                "--no-gui",
                "--no-browser",
                "--disable-playwright",
                "--no-fancy-input",
                "--no-multiline",
                "--no-notifications",

                # Suppress model warning browser/page noise for unknown local models.
                "--no-show-model-warnings",
                "--no-check-model-accepts-settings",

                # Use the isolated sandbox repo, not the parent VillaniBench repo.
                "--git",

                # Prevent Aider commits.
                "--no-auto-commits",
                "--no-dirty-commits",

                # Stable logs.
                "--no-stream",
                "--no-pretty",
                "--analytics-disable",
                "--no-check-update",
                "--no-show-release-notes",

                # Benchmark safety.
                "--no-auto-lint",
                "--no-auto-test",
                "--no-detect-urls",
                "--no-suggest-shell-commands",
                "--no-watch-files",

                "--encoding",
                "utf-8",
                "--show-diffs",
            ]

            env = os.environ.copy()

            for key in [
                "AIDER_MODEL",
                "AIDER_CONFIG",
                "AIDER_ENV_FILE",
                "AIDER_GUI",
                "AIDER_BROWSER",
                "AIDER_SHOW_MODEL_WARNINGS",
                "AIDER_CHECK_MODEL_ACCEPTS_SETTINGS",
                "AIDER_NOTIFICATIONS",
                "AIDER_ANALYTICS_DISABLE",
                "AIDER_CHECK_UPDATE",
                "AIDER_SHOW_RELEASE_NOTES",
                "OPENAI_API_BASE",
                "OPENAI_API_KEY",
                "LM_STUDIO_API_BASE",
                "LM_STUDIO_API_KEY",
                "OPENROUTER_API_KEY",
                "ANTHROPIC_API_KEY",
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_INDEX_FILE",
            ]:
                env.pop(key, None)

            env.update(model_config.env)

            env["AIDER_ANALYTICS_DISABLE"] = "true"
            env["AIDER_CHECK_UPDATE"] = "false"
            env["AIDER_SHOW_RELEASE_NOTES"] = "false"
            env["AIDER_SHOW_MODEL_WARNINGS"] = "false"
            env["AIDER_CHECK_MODEL_ACCEPTS_SETTINGS"] = "false"
            env["AIDER_GUI"] = "false"
            env["AIDER_BROWSER"] = "false"
            env["AIDER_NOTIFICATIONS"] = "false"
            env["NO_COLOR"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            # Stop git discovery from walking up into the outer VillaniBench repo.
            env["GIT_CEILING_DIRECTORIES"] = str(sandbox_dir)

            redacted_values = {
                str(config.get("api_key") or ""),
                env.get("OPENAI_API_KEY", ""),
                env.get("LM_STUDIO_API_KEY", ""),
                env.get("OPENROUTER_API_KEY", ""),
                env.get("ANTHROPIC_API_KEY", ""),
            }

            redacted_argv = _build_redacted_argv(argv, redacted_values)
            raw_command = " ".join(shlex.quote(str(x)) for x in redacted_argv)

            command_path.write_text(
                json.dumps(
                    {
                        "argv": redacted_argv,
                        "cwd": str(cwd),
                        "timeout": budget.wall_time_sec,
                        "provider": model_config.provider,
                        "model": model_config.model,
                        "config_file": str(config_path),
                        "env_file": str(env_file_path),
                        "aiderignore_file": str(aiderignore_path),
                        "model_metadata_file": str(model_metadata_path),
                        "prompt_file": str(prompt_path),
                        "prompt_is_verbatim_benchmark_prompt": True,
                        "uses_oracle_expected_files": False,
                        "passes_file_hints": False,
                        "created_isolated_git_repo": created_git_repo,
                        "git_ceiling_directories": env["GIT_CEILING_DIRECTORIES"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = run_command_tree_argv(
                argv,
                cwd,
                budget.wall_time_sec,
                env=env,
                stdin_text=None,
            )

            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")

            result_path.write_text(
                json.dumps(
                    {
                        "exit_code": completed.exit_code,
                        "timed_out": completed.timed_out,
                        "wall_time_sec": completed.wall_time_sec,
                        "provider": model_config.provider,
                        "model": model_config.model,
                        "prompt_file": str(prompt_path),
                        "prompt_is_verbatim_benchmark_prompt": True,
                        "uses_oracle_expected_files": False,
                        "passes_file_hints": False,
                        "created_isolated_git_repo": created_git_repo,
                        "config_file": str(config_path),
                        "env_file": str(env_file_path),
                        "aiderignore_file": str(aiderignore_path),
                        "model_metadata_file": str(model_metadata_path),
                        "command_redacted": redacted_argv,
                        "stdout_file": str(stdout_path),
                        "stderr_file": str(stderr_path),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            ended = now_iso()

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

            try:
                result_path.write_text(
                    json.dumps(
                        {
                            "exit_code": 1,
                            "timed_out": False,
                            "runner_crashed": True,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "prompt_is_verbatim_benchmark_prompt": True,
                            "uses_oracle_expected_files": False,
                            "passes_file_hints": False,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            except Exception:
                pass

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