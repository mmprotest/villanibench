from __future__ import annotations

import subprocess
import time
from pathlib import Path

from villanibench.harness.llm import ChatClient, ChatMessage, OpenAICompatibleChatClient
from villanibench.harness.telemetry import Telemetry

from .base import AdapterRunResult, RunnerAdapter, now_iso


def resolve_repo_path(repo_root: Path, raw_path: str) -> Path | None:
    if not raw_path:
        return None
    candidate_raw = Path(raw_path)
    if candidate_raw.is_absolute():
        return None
    candidate = (repo_root / candidate_raw).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return candidate


class MinimalReactControlAdapter(RunnerAdapter):
    name = "minimal_react_control"

    def __init__(self, chat_client: ChatClient | None = None):
        self._chat_client = chat_client
        self._telem = Telemetry(
            model_calls=0,
            tokens_input=0,
            tokens_output=0,
            shell_commands=0,
            file_reads=0,
            file_writes=0,
            telemetry_completeness="complete",
            missing_telemetry=[],
        )

    def _client(self, config: dict) -> ChatClient:
        if self._chat_client is not None:
            return self._chat_client
        factory = config.get("chat_client_factory")
        if factory:
            return factory(config)
        return OpenAICompatibleChatClient(base_url=str(config["base_url"]), api_key=str(config.get("api_key") or "dummy"))

    def _parse_action(self, text: str) -> tuple[str | None, dict[str, str]]:
        lines = [line.rstrip("\n") for line in text.splitlines()]
        if not lines or not lines[0].startswith("ACTION: "):
            return None, {}
        action = lines[0].split(":", 1)[1].strip()
        fields: dict[str, str] = {}
        i = 1
        while i < len(lines):
            line = lines[i]
            if line.startswith("CONTENT:"):
                i += 1
                content_lines: list[str] = []
                while i < len(lines) and lines[i] != "END_CONTENT":
                    content_lines.append(lines[i])
                    i += 1
                fields["CONTENT"] = "\n".join(content_lines)
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
            i += 1
        return action, fields

    def _finish_telem(self) -> None:
        if self._telem.tokens_input in (None, 0) and self._telem.tokens_output in (None, 0):
            self._telem.telemetry_completeness = "partial"
            self._telem.missing_telemetry = ["tokens_input", "tokens_output"]

    def run(self, task, sandbox_dir: Path, budget, config: dict) -> AdapterRunResult:
        self._telem = Telemetry(
            model_calls=0,
            tokens_input=0,
            tokens_output=0,
            shell_commands=0,
            file_reads=0,
            file_writes=0,
            telemetry_completeness="complete",
            missing_telemetry=[],
        )
        patch_attempts = 0
        invalid_actions = 0
        blocked_finish_attempts = 0
        wrote_files = False
        last_write_step: int | None = None
        last_visible_test_step: int | None = None
        step = 0

        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        repo_root = (sandbox_dir / "repo").resolve()
        prompt_path = sandbox_dir / "prompt.txt"
        prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        started = now_iso()
        cmd = "model_backed_minimal_react_control_loop"
        timed_out = False
        exit_code = 0
        runner_crashed = False
        client = self._client(config)
        model = str(config.get("model", ""))
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are minimal_react_control, a simple coding agent used as a benchmark control.\n"
                    "You must solve the task by inspecting files, running visible tests, and making minimal edits.\n"
                    "You only have access to the repository and visible tests.\n"
                    "Do not assume hidden tests.\n"
                    "Do not modify tests.\n"
                    "Do not make broad rewrites.\n\n"
                    "Respond with exactly one action in this format:\n"
                    "ACTION: list_files\nPATH: .\n\n"
                    "or\n\n"
                    "ACTION: read_file\nPATH: src/example.py\n\n"
                    "or\n\n"
                    "ACTION: search\nQUERY: DEFAULT_RETRIES\n\n"
                    "or\n\n"
                    "ACTION: run_tests\n\n"
                    "or\n\n"
                    "ACTION: write_file\nPATH: src/example.py\nCONTENT:\n<full new file content>\nEND_CONTENT\n\n"
                    "or\n\n"
                    "ACTION: finish\nREASON: <short reason>\n\n"
                    "No markdown.\nNo extra prose."
                ),
            ),
            ChatMessage(
                role="user",
                content=f"Task prompt:\n{prompt_text}\n\nVisible test command:\n{task.visible_test_command}\n\nRepository root is current workspace.",
            ),
        ]

        with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
            deadline = time.monotonic() + budget.wall_time_sec
            while True:
                step += 1
                if time.monotonic() >= deadline:
                    timed_out = True
                    exit_code = 124
                    break
                if (self._telem.model_calls or 0) >= budget.max_model_calls:
                    break
                if patch_attempts >= budget.max_patch_attempts:
                    break
                try:
                    response = client.create_chat_completion(
                        model=model,
                        messages=messages,
                        temperature=0,
                        max_tokens=2048,
                    )
                    self._telem.model_calls = (self._telem.model_calls or 0) + 1
                    if response.prompt_tokens is None or response.completion_tokens is None:
                        self._telem.telemetry_completeness = "partial"
                    else:
                        self._telem.tokens_input = (self._telem.tokens_input or 0) + response.prompt_tokens
                        self._telem.tokens_output = (self._telem.tokens_output or 0) + response.completion_tokens
                    out.write(f"{response.content}\n")
                except Exception as exc:
                    err.write(f"Chat client error: {exc}\n")
                    runner_crashed = True
                    exit_code = 1
                    break

                action, fields = self._parse_action(response.content)
                obs = ""
                if action == "list_files":
                    rel_path = fields.get("PATH", ".")
                    base = resolve_repo_path(repo_root, rel_path)
                    if base is None or not base.exists() or not base.is_dir():
                        obs = "Invalid PATH. Use relative directory under repo."
                    else:
                        files = sorted(p.relative_to(repo_root).as_posix() for p in base.rglob("*") if p.is_file())
                        obs = "\n".join(files[:200]) if files else "(no files)"
                elif action == "read_file":
                    rel_path = fields.get("PATH", "")
                    file_path = resolve_repo_path(repo_root, rel_path)
                    if (
                        file_path is None
                        or not file_path.exists()
                        or not file_path.is_file()
                        or (self._telem.file_reads or 0) >= budget.max_file_reads
                    ):
                        obs = "Invalid read_file action or file read budget reached."
                    else:
                        self._telem.file_reads = (self._telem.file_reads or 0) + 1
                        text = file_path.read_text(encoding="utf-8", errors="replace")
                        obs = text[:16000] + ("\n...[TRUNCATED]..." if len(text) > 16000 else "")
                elif action == "search":
                    query = fields.get("QUERY", "")
                    rel_path = fields.get("PATH")
                    if not query:
                        obs = "QUERY is required."
                    else:
                        search_root = repo_root
                        if rel_path:
                            resolved = resolve_repo_path(repo_root, rel_path)
                            if resolved is None or not resolved.exists() or not resolved.is_dir():
                                obs = "Invalid PATH. Use relative directory under repo."
                                messages.append(ChatMessage(role="assistant", content=response.content))
                                messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
                                continue
                            search_root = resolved
                        results: list[str] = []
                        for p in search_root.rglob("*"):
                            if not p.is_file() or any(part in {".git", "__pycache__", ".pytest_cache", ".venv", "venv"} for part in p.parts):
                                continue
                            txt = p.read_text(encoding="utf-8", errors="ignore")
                            for idx, line in enumerate(txt.splitlines(), start=1):
                                if query in line:
                                    results.append(f"{p.relative_to(repo_root).as_posix()}:{idx}: {line[:200]}")
                                    if len(results) >= 200:
                                        break
                            if len(results) >= 200:
                                break
                        obs = "\n".join(results) if results else "(no matches)"
                elif action == "run_tests":
                    if (self._telem.shell_commands or 0) >= budget.max_shell_commands:
                        obs = "Shell command budget exceeded."
                    else:
                        self._telem.shell_commands = (self._telem.shell_commands or 0) + 1
                        last_visible_test_step = step
                        remaining = max(1, int(deadline - time.monotonic()))
                        try:
                            res = subprocess.run(
                                task.visible_test_command,
                                cwd=sandbox_dir,
                                shell=True,
                                text=True,
                                capture_output=True,
                                timeout=remaining,
                            )
                            obs = f"exit_code={res.returncode}\nSTDOUT:\n{res.stdout[:6000]}\nSTDERR:\n{res.stderr[:4000]}"
                        except subprocess.TimeoutExpired:
                            obs = "run_tests timed out."
                elif action == "write_file":
                    rel_path = fields.get("PATH", "")
                    if rel_path.startswith("tests/") or "/tests/" in rel_path or "\\tests\\" in rel_path or rel_path.startswith("repo/tests/"):
                        obs = "Refused: tests modification is not allowed."
                    else:
                        file_path = resolve_repo_path(repo_root, rel_path)
                        if (
                            file_path is None
                            or (self._telem.file_writes or 0) >= budget.max_file_writes
                            or patch_attempts >= budget.max_patch_attempts
                        ):
                            obs = "Invalid write_file action or write budget reached."
                        else:
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            file_path.write_text(fields.get("CONTENT", ""), encoding="utf-8")
                            self._telem.file_writes = (self._telem.file_writes or 0) + 1
                            patch_attempts += 1
                            wrote_files = True
                            last_write_step = step
                            obs = "write_file ok"
                elif action == "finish":
                    if wrote_files and (last_visible_test_step is None or (last_write_step is not None and last_visible_test_step <= last_write_step)):
                        blocked_finish_attempts += 1
                        obs = "You modified files but have not run visible tests after the latest edit. Run ACTION: run_tests before finishing."
                        if blocked_finish_attempts > 3:
                            runner_crashed = True
                            exit_code = 1
                            err.write(
                                "finish blocked repeatedly after writes without visible verification; stopping after more than 3 attempts.\n"
                            )
                            messages.append(ChatMessage(role="assistant", content=response.content))
                            messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
                            break
                    else:
                        obs = f"finish: {fields.get('REASON', '')}"
                        messages.append(ChatMessage(role="assistant", content=response.content))
                        messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
                        break
                else:
                    invalid_actions += 1
                    obs = "Invalid action. Use ACTION with one of list_files/read_file/search/run_tests/write_file/finish."
                    if invalid_actions > 3:
                        runner_crashed = True
                        exit_code = 1
                        messages.append(ChatMessage(role="assistant", content=response.content))
                        messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
                        break

                messages.append(ChatMessage(role="assistant", content=response.content))
                messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
        ended = now_iso()
        self._finish_telem()
        return AdapterRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at=started,
            ended_at=ended,
            timed_out=timed_out,
            runner_crashed=runner_crashed,
            raw_command=cmd,
            comparison_mode="strict",
            control_kind="model_backed",
            setting_warnings=[],
        )

    def collect_telemetry(self, sandbox_dir: Path) -> Telemetry:
        return self._telem
