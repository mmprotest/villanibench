from __future__ import annotations

import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from villanibench.harness.process import run_command_tree_argv

from .base import AdapterRunResult, RunnerAdapter, now_iso


def normalize_aider_model(model: Any) -> str:
    value = str(model or "").strip()
    if not value:
        raise ValueError("Aider adapter requires model")
    if "/" in value:
        return value
    return f"openai/{value}"


def _safe_expected_files(task: Any, workspace: Path) -> list[str]:
    oracle = Path(getattr(task, "task_dir", workspace)) / "oracle" / "expected_files.json"
    if not oracle.exists() or not oracle.is_file():
        return []
    try:
        payload = json.loads(oracle.read_text(encoding="utf-8"))
    except Exception:
        return []

    candidates = list(payload.get("expected_files", [])) + list(payload.get("strongly_expected_files", []))
    safe: list[str] = []
    for raw in candidates:
        rel = Path(str(raw))
        if rel.is_absolute() or ".." in rel.parts:
            continue
        resolved = (workspace / rel).resolve()
        try:
            resolved.relative_to(workspace.resolve())
        except ValueError:
            continue
        if not resolved.exists() or not resolved.is_file():
            continue
        safe.append(rel.as_posix())
    return safe


def _build_prompt(task: Any, task_instructions: str, expected_files: list[str]) -> str:
    verify = str(getattr(task, "visible_test_command", "")).strip() or "Not provided"
    expected = "\n".join(expected_files) if expected_files else "Not provided"
    return (
        "You are running inside an isolated benchmark workspace.\n\n"
        "Modify the repository files to satisfy the task below.\n\n"
        "Rules:\n"
        "- Make the smallest correct code change.\n"
        "- Edit files directly.\n"
        "- Do not ask questions.\n"
        "- Do not explain instead of editing.\n"
        "- Do not create unrelated files.\n"
        "- Do not commit changes.\n"
        "- Do not run long-running servers.\n"
        "- Use the task instructions and existing tests as the source of truth.\n"
        "- When finished, stop.\n\n"
        "Task:\n"
        f"{task_instructions}\n\n"
        "Visible verification:\n"
        f"{verify}\n\n"
        "Expected files:\n"
        f"{expected}\n"
    )


class AiderAdapter(RunnerAdapter):
    name = "aider"

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        output_dir = Path(config["task_output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        cwd = (sandbox_dir / "repo").resolve()

        stdout_path = output_dir / "aider_stdout.txt"
        stderr_path = output_dir / "aider_stderr.txt"
        prompt_path = output_dir / "aider_prompt.txt"
        command_path = output_dir / "aider_command.json"
        result_path = output_dir / "aider_result.json"

        started = now_iso()
        try:
            exe = shutil.which("aider") or shutil.which("aider.cmd") or "aider"
            normalized_model = normalize_aider_model(config.get("model"))
            base_url = str(config.get("base_url") or "").strip()
            api_key = str(config.get("api_key") or "dummy")

            prompt_src = (sandbox_dir / "prompt.txt")
            task_text = prompt_src.read_text(encoding="utf-8") if prompt_src.exists() else ""
            expected_files = _safe_expected_files(task, cwd)
            prompt_text = _build_prompt(task, task_text, expected_files)
            prompt_path.write_text(prompt_text, encoding="utf-8")

            argv = [
                exe,
                "--model", normalized_model,
                "--openai-api-base", base_url,
                "--openai-api-key", api_key,
                "--message-file", str(prompt_path),
                "--yes-always",
                "--no-auto-commits",
                "--no-dirty-commits",
                "--no-stream",
                "--no-pretty",
                "--analytics-disable",
                "--no-check-update",
                "--no-show-release-notes",
                "--no-gitignore",
                "--no-auto-lint",
                "--no-auto-test",
                "--encoding", "utf-8",
                "--show-diffs",
            ]
            for rel in expected_files:
                argv.extend(["--file", rel])

            redacted = ["<redacted>" if x == api_key else x for x in argv]
            env = os.environ.copy()
            env["OPENAI_API_BASE"] = base_url
            env["OPENAI_API_KEY"] = api_key
            env["AIDER_ANALYTICS_DISABLE"] = "true"
            env["AIDER_CHECK_UPDATE"] = "false"
            env["AIDER_SHOW_RELEASE_NOTES"] = "false"
            env["NO_COLOR"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            completed = run_command_tree_argv(argv, cwd, budget.wall_time_sec, env=env, stdin_text=None)
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")

            command_path.write_text(json.dumps({"argv": redacted, "cwd": str(cwd), "timeout": budget.wall_time_sec}, indent=2) + "\n", encoding="utf-8")
            result_path.write_text(
                json.dumps(
                    {
                        "exit_code": completed.exit_code,
                        "timed_out": completed.timed_out,
                        "wall_time_sec": completed.wall_time_sec,
                        "normalized_model": normalized_model,
                        "prompt_file": str(prompt_path),
                        "command_redacted": redacted,
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
                raw_command=" ".join(shlex.quote(str(x)) for x in redacted),
                comparison_mode="strict",
                control_kind=None,
                setting_warnings=[],
                notes=None,
            )
        except Exception as exc:
            stderr_path.write_text(f"Adapter execution error: {exc}\n", encoding="utf-8")
            stdout_path.write_text("", encoding="utf-8")
            ended = now_iso()
            return AdapterRunResult(
                exit_code=1,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                started_at=started,
                ended_at=ended,
                timed_out=False,
                runner_crashed=True,
                raw_command="aider",
                comparison_mode="strict",
            )
