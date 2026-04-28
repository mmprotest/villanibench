from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

from villanibench.harness.llm import ChatClient, ChatMessage, OpenAICompatibleChatClient
from villanibench.harness.notes import append_note
from villanibench.harness.telemetry import Telemetry

from .base import AdapterRunResult, RunnerAdapter, now_iso


IGNORED_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".venv",
    "venv",
    "node_modules",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd"}
TRACE_TEXT_LIMIT = 8000


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


def should_ignore_path(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in IGNORED_PATH_PARTS for part in rel.parts):
        return True
    if path.suffix in IGNORED_SUFFIXES:
        return True
    return any(part.endswith(".egg-info") for part in rel.parts)


def _short_digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _truncate_text(text: str) -> tuple[str, bool]:
    if len(text) <= TRACE_TEXT_LIMIT:
        return text, False
    return text[:TRACE_TEXT_LIMIT], True


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
            elif line.startswith("OLD:"):
                i += 1
                old_lines: list[str] = []
                while i < len(lines) and lines[i] != "END_OLD":
                    old_lines.append(lines[i])
                    i += 1
                fields["OLD"] = "\n".join(old_lines)
            elif line.startswith("NEW:"):
                i += 1
                new_lines: list[str] = []
                while i < len(lines) and lines[i] != "END_NEW":
                    new_lines.append(lines[i])
                    i += 1
                fields["NEW"] = "\n".join(new_lines)
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
            i += 1
        return action, fields

    def _action_signature(self, action: str | None, fields: dict[str, str]) -> str:
        if action is None:
            return "invalid_action"
        if action in {"list_files", "read_file", "search"}:
            value = fields.get("PATH", ".") if action != "search" else fields.get("QUERY", "")
            return f"{action}:{value}"
        if action in {"run_tests", "finish"}:
            return action
        if action == "replace_text":
            return (
                f"replace_text:{fields.get('PATH', '')}:{_short_digest(fields.get('OLD', ''))}:{_short_digest(fields.get('NEW', ''))}"
            )
        if action == "write_file":
            return f"write_file:{fields.get('PATH', '')}:{_short_digest(fields.get('CONTENT', ''))}"
        return f"{action}:{fields.get('PATH', '')}"

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
        blocked_repeat_count = 0
        wrote_files = False
        last_write_step: int | None = None
        last_visible_test_step: int | None = None
        step = 0

        output_dir = Path(config["task_output_dir"])
        stdout_path = output_dir / "runner_stdout.txt"
        stderr_path = output_dir / "runner_stderr.txt"
        trace_path = output_dir / "control_trace.jsonl"
        repo_root = (sandbox_dir / "repo").resolve()
        prompt_path = sandbox_dir / "prompt.txt"
        prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        started = now_iso()
        start_monotonic = time.monotonic()
        cmd = "model_backed_minimal_react_control_loop"
        timed_out = False
        exit_code = 0
        runner_crashed = False
        budget_exceeded = False
        runner_notes: str | None = None
        crash_reason: str | None = None
        client = self._client(config)
        model = str(config.get("model", ""))
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are minimal_react_control, a simple benchmark control runner.\n\n"
                    "Use this default workflow:\n"
                    "1. List files once to understand the repo.\n"
                    "2. Search for terms from the user task or failing test output.\n"
                    "3. Read likely source files.\n"
                    "4. Run visible tests to see the failure.\n"
                    "5. Make the smallest source-code edit.\n"
                    "6. Run visible tests again after every edit.\n"
                    "7. Finish only after visible tests pass or you are unable to proceed.\n\n"
                    "Rules:\n"
                    "- Do not modify tests.\n"
                    "- Do not assume hidden tests.\n"
                    "- Do not repeatedly list the same directory.\n"
                    "- Do not repeatedly read the same file unless something changed.\n"
                    "- Prefer replace_text for small edits.\n"
                    "- Use write_file only when replace_text is not practical.\n"
                    "- If an action returns useful information, use it in the next action.\n\n"
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
                    "ACTION: replace_text\nPATH: src/example.py\nOLD:\n<exact old text>\nEND_OLD\nNEW:\n<exact new text>\nEND_NEW\n\n"
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

        previous_signature = ""
        repeated_action_count = 0

        with (
            stdout_path.open("w", encoding="utf-8") as out,
            stderr_path.open("w", encoding="utf-8") as err,
            trace_path.open("w", encoding="utf-8") as trace,
        ):
            deadline = time.monotonic() + budget.wall_time_sec
            while True:
                step += 1
                if time.monotonic() >= deadline:
                    timed_out = True
                    exit_code = 124
                    crash_reason = "wall time exceeded"
                    break
                if (self._telem.model_calls or 0) >= budget.max_model_calls:
                    runner_crashed = True
                    exit_code = 1
                    budget_exceeded = True
                    crash_reason = "max model calls reached"
                    runner_notes = append_note(runner_notes, "minimal_react_control reached max_model_calls before finishing.")
                    break
                if patch_attempts >= budget.max_patch_attempts:
                    runner_crashed = True
                    exit_code = 1
                    crash_reason = "patch attempts exceeded"
                    runner_notes = append_note(runner_notes, "minimal_react_control reached max_patch_attempts before finishing.")
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
                    crash_reason = "backend request failure"
                    runner_notes = append_note(runner_notes, f"minimal_react_control backend request failed: {exc}")
                    break

                action, fields = self._parse_action(response.content)
                action_signature = self._action_signature(action, fields)
                if action_signature == previous_signature:
                    repeated_action_count += 1
                else:
                    previous_signature = action_signature
                    repeated_action_count = 1

                obs = ""
                action_valid = True
                error: str | None = None
                skip_execute_due_repeat = repeated_action_count >= 3 and action_signature in {
                    "invalid_action",
                    "run_tests",
                } or (repeated_action_count >= 3 and action in {"list_files", "read_file", "search"})

                if skip_execute_due_repeat:
                    blocked_repeat_count += 1
                    obs = (
                        "You have already performed this action several times without progress. "
                        "Choose a different action: search, read_file, run_tests, replace_text, write_file, or finish."
                    )
                    error = "blocked_repeat"
                elif action == "list_files":
                    rel_path = fields.get("PATH", ".")
                    base = resolve_repo_path(repo_root, rel_path)
                    if base is None or not base.exists() or not base.is_dir():
                        obs = "Invalid PATH. Use relative directory under repo."
                    else:
                        files = sorted(
                            p.relative_to(repo_root).as_posix()
                            for p in base.rglob("*")
                            if p.is_file() and not should_ignore_path(p, repo_root)
                        )
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
                            if not p.is_file() or should_ignore_path(p, repo_root):
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
                            previous_signature = ""
                            repeated_action_count = 0
                            obs = "write_file ok"
                elif action == "replace_text":
                    rel_path = fields.get("PATH", "")
                    if rel_path.startswith("tests/") or "/tests/" in rel_path or "\\tests\\" in rel_path or rel_path.startswith("repo/tests/"):
                        obs = "Refused: tests modification is not allowed."
                    else:
                        file_path = resolve_repo_path(repo_root, rel_path)
                        if (
                            file_path is None
                            or not file_path.exists()
                            or not file_path.is_file()
                            or (self._telem.file_writes or 0) >= budget.max_file_writes
                            or patch_attempts >= budget.max_patch_attempts
                        ):
                            obs = "Invalid replace_text action or write budget reached."
                        else:
                            raw = file_path.read_bytes()
                            if b"\x00" in raw:
                                obs = "Refused: binary files are not supported."
                            else:
                                try:
                                    current = raw.decode("utf-8")
                                except UnicodeDecodeError:
                                    obs = "Refused: binary files are not supported."
                                else:
                                    old = fields.get("OLD", "")
                                    new = fields.get("NEW", "")
                                    count = current.count(old)
                                    if count == 0:
                                        obs = "OLD text not found."
                                    elif count > 1:
                                        obs = "OLD text is ambiguous and occurs multiple times."
                                    else:
                                        updated = current.replace(old, new, 1)
                                        file_path.write_text(updated, encoding="utf-8")
                                        self._telem.file_writes = (self._telem.file_writes or 0) + 1
                                        patch_attempts += 1
                                        wrote_files = True
                                        last_write_step = step
                                        previous_signature = ""
                                        repeated_action_count = 0
                                        obs = "replace_text ok"
                elif action == "finish":
                    if wrote_files and (last_visible_test_step is None or (last_write_step is not None and last_visible_test_step <= last_write_step)):
                        blocked_finish_attempts += 1
                        obs = "You modified files but have not run visible tests after the latest edit. Run ACTION: run_tests before finishing."
                        if blocked_finish_attempts > 3:
                            runner_crashed = True
                            exit_code = 1
                            crash_reason = "repeated blocked finish without verification"
                            runner_notes = append_note(
                                runner_notes,
                                "minimal_react_control stopped after repeated blocked finish attempts without visible verification.",
                            )
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
                else:
                    invalid_actions += 1
                    action_valid = False
                    error = "parse_error"
                    obs = "Invalid action. Use ACTION with one of list_files/read_file/search/run_tests/write_file/replace_text/finish."
                    if invalid_actions > 3:
                        runner_crashed = True
                        exit_code = 1
                        crash_reason = "too many invalid actions"
                        runner_notes = append_note(runner_notes, "minimal_react_control stopped after too many invalid actions.")
                        messages.append(ChatMessage(role="assistant", content=response.content))
                        messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
                        break

                if repeated_action_count == 2 and not skip_execute_due_repeat:
                    obs = (
                        f"{obs}\nYou repeated the same action. "
                        "Use the result and choose a different next action."
                    )
                if blocked_repeat_count > 3:
                    runner_crashed = True
                    exit_code = 1
                    crash_reason = "repeated identical actions"
                    runner_notes = append_note(
                        runner_notes,
                        "minimal_react_control stopped after repeated identical actions without progress.",
                    )

                model_output, model_trunc = _truncate_text(response.content)
                tool_result, tool_trunc = _truncate_text(obs)
                trace.write(
                    json.dumps(
                        {
                            "step": step,
                            "elapsed_sec": round(time.monotonic() - start_monotonic, 4),
                            "model_output": model_output,
                            "model_output_truncated": model_trunc,
                            "parsed_action": action,
                            "parsed_args": fields,
                            "valid_action": action_valid,
                            "tool_result": tool_result,
                            "tool_result_truncated": tool_trunc,
                            "error": error,
                            "repeated_action_count": repeated_action_count,
                        }
                    )
                    + "\n"
                )
                trace.flush()

                if runner_crashed:
                    break
                if action == "finish" and obs.startswith("finish:"):
                    break

                messages.append(ChatMessage(role="assistant", content=response.content))
                messages.append(ChatMessage(role="user", content=f"OBSERVATION:\n{obs}"))
            trace.write(json.dumps({"event": "final", "status": "runner_crash" if runner_crashed else "ok", "reason": crash_reason}) + "\n")
            trace.flush()

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
            notes=runner_notes,
            trace_path=trace_path,
            budget_exceeded=budget_exceeded,
        )

    def collect_telemetry(self, sandbox_dir: Path) -> Telemetry:
        return self._telem
