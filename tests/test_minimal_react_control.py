import json
from pathlib import Path
from typing import Callable

import pytest

from villanibench.cli import main
from villanibench.harness.adapters.minimal_react_control import MinimalReactControlAdapter
from villanibench.harness.budget import BudgetProfile
from villanibench.harness.budget import get_budget_profile
from villanibench.harness.llm import ChatMessage, ChatResponse
from villanibench.harness.run import run_suite
from villanibench.tasks.loader import load_task


SUITE_DIR = Path("suites/core_v0_1")
VB_MIN_001 = load_task(SUITE_DIR / "tasks" / "VB-MIN-001")


class FakeChatClient:
    def __init__(self):
        self.calls = 0
        self._step = 0
        self._task_marker = ""

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        self.calls += 1
        joined = "\n".join(m.content for m in messages)
        assert "tests/hidden" not in joined
        task_marker = messages[1].content
        if task_marker != self._task_marker:
            self._task_marker = task_marker
            self._step = 0
        self._step += 1
        if "default retry count" not in task_marker.lower():
            return ChatResponse("ACTION: finish\nREASON: skip", prompt_tokens=1, completion_tokens=1)
        if self._step == 1:
            return ChatResponse("ACTION: read_file\nPATH: src/demo_cli/config.py", prompt_tokens=10, completion_tokens=8)
        if self._step == 2:
            content = (
                "ACTION: replace_text\n"
                "PATH: src/demo_cli/config.py\n"
                "OLD:\nDEFAULT_RETRIES = 5\nEND_OLD\n"
                "NEW:\nDEFAULT_RETRIES = 3\nEND_NEW"
            )
            return ChatResponse(content, prompt_tokens=11, completion_tokens=10)
        if self._step == 3:
            return ChatResponse("ACTION: run_tests", prompt_tokens=8, completion_tokens=3)
        return ChatResponse("ACTION: finish\nREASON: done", prompt_tokens=6, completion_tokens=3)


class ScriptedChatClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls = 0

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return ChatResponse(self.responses[idx], prompt_tokens=1, completion_tokens=1)


class SequencedChatClient:
    def __init__(self, scripts_per_run: list[list[str]]):
        self.scripts_per_run = scripts_per_run
        self.run_index = -1
        self.call_index = 0

    def start_run(self):
        self.run_index += 1
        self.call_index = 0

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        script = self.scripts_per_run[self.run_index]
        idx = min(self.call_index, len(script) - 1)
        self.call_index += 1
        return ChatResponse(script[idx], prompt_tokens=1, completion_tokens=1)


class ObservationCheckingChatClient:
    def __init__(self, actions: list[str], checks: list[Callable[[str], None]]):
        self.actions = actions
        self.checks = checks
        self.calls = 0

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        if self.calls > 0 and self.calls - 1 < len(self.checks):
            observation = messages[-1].content
            self.checks[self.calls - 1](observation)
        idx = min(self.calls, len(self.actions) - 1)
        self.calls += 1
        return ChatResponse(self.actions[idx], prompt_tokens=1, completion_tokens=1)


class PromptCaptureClient:
    def __init__(self):
        self.system_prompt = ""

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        self.system_prompt = messages[0].content
        return ChatResponse("ACTION: finish\nREASON: done", prompt_tokens=1, completion_tokens=1)


def _run_adapter(adapter: MinimalReactControlAdapter, chat_client: SequencedChatClient | ScriptedChatClient, sandbox_dir: Path, output_dir: Path):
    if hasattr(chat_client, "start_run"):
        chat_client.start_run()
    return adapter.run(
        VB_MIN_001,
        sandbox_dir,
        get_budget_profile("lite_v0_1"),
        {"task_output_dir": str(output_dir), "model": "dummy", "base_url": "http://localhost"},
    )


def test_minimal_control_model_backed_loop_solves_task(tmp_path: Path, monkeypatch):
    fake = FakeChatClient()
    adapter = MinimalReactControlAdapter(chat_client=fake)
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(SUITE_DIR, "minimal_react_control", "dummy-model", out, {"base_url": "http://localhost:1234", "api_key": "dummy"})

    task_dir = out / "tasks" / "VB-MIN-001"
    result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    diff_text = (task_dir / "final.diff").read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["control_kind"] == "model_backed"
    assert result["comparison_mode"] == "strict"
    assert result["model_calls"] > 0
    assert result["file_reads"] > 0
    assert result["file_writes"] > 0
    assert result["success_hidden"] is True
    assert result["patch_size_lines"] <= 4
    assert "+DEFAULT_RETRIES = 3" in diff_text
    assert "tests/hidden" not in diff_text


def test_minimal_control_resets_per_task_state_between_runs(tmp_path: Path):
    scripts = [
        [
            "ACTION: read_file\nPATH: src/demo_cli/config.py",
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\nDEFAULT_RETRIES = 3\nEND_CONTENT",
            "ACTION: run_tests",
            "ACTION: finish\nREASON: done",
        ],
        [
            "ACTION: finish\nREASON: no-op",
        ],
    ]
    chat = SequencedChatClient(scripts)
    adapter = MinimalReactControlAdapter(chat_client=chat)

    for idx in (1, 2):
        sandbox = tmp_path / f"sandbox_{idx}"
        out = tmp_path / f"out_{idx}"
        (out).mkdir(parents=True)
        (sandbox / "repo/src/demo_cli").mkdir(parents=True)
        (sandbox / "repo/src/demo_cli/config.py").write_text('"""Config constants for the demo CLI."""\n\nDEFAULT_RETRIES = 5\n', encoding="utf-8")
        (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
        _run_adapter(adapter, chat, sandbox, out)
        telem = adapter.collect_telemetry(sandbox)
        if idx == 1:
            assert telem.model_calls == 4
            assert telem.file_reads == 1
            assert telem.file_writes == 1
            assert telem.shell_commands == 1
        else:
            assert telem.model_calls == 1
            assert telem.file_reads == 0
            assert telem.file_writes == 0
            assert telem.shell_commands == 0


def test_minimal_control_patch_attempt_budget_is_per_task(tmp_path: Path):
    scripts = [
        [
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\na=1\nEND_CONTENT",
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\na=2\nEND_CONTENT",
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\na=3\nEND_CONTENT",
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\na=4\nEND_CONTENT",
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\na=5\nEND_CONTENT",
            "ACTION: finish\nREASON: done",
        ],
        [
            "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\nb=1\nEND_CONTENT",
            "ACTION: run_tests",
            "ACTION: finish\nREASON: done",
        ],
    ]
    chat = SequencedChatClient(scripts)
    adapter = MinimalReactControlAdapter(chat_client=chat)
    for idx in (1, 2):
        sandbox = tmp_path / f"sandbox_budget_{idx}"
        out = tmp_path / f"out_budget_{idx}"
        out.mkdir(parents=True)
        (sandbox / "repo/src/demo_cli").mkdir(parents=True)
        (sandbox / "repo/src/demo_cli/config.py").write_text("x=0\n", encoding="utf-8")
        (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
        _run_adapter(adapter, chat, sandbox, out)
        telem = adapter.collect_telemetry(sandbox)
        if idx == 1:
            assert telem.file_writes == 5
        else:
            assert telem.file_writes == 1


def test_path_safety_rejects_parent_traversal_read(tmp_path: Path):
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: read_file\nPATH: ../secret.txt", "ACTION: finish\nREASON: done"]))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    log = (out / "runner_stdout.txt").read_text(encoding="utf-8")
    assert "ACTION: read_file" in log
    assert "../secret.txt" in log


def test_path_safety_rejects_write_outside_and_tests(tmp_path: Path):
    responses = [
        "ACTION: write_file\nPATH: ../secret.txt\nCONTENT:\nx\nEND_CONTENT",
        f"ACTION: write_file\nPATH: {(tmp_path / 'outside.py').as_posix()}\nCONTENT:\nx\nEND_CONTENT",
        "ACTION: write_file\nPATH: tests/test_x.py\nCONTENT:\nx\nEND_CONTENT",
        "ACTION: write_file\nPATH: src/../tests/test_x.py\nCONTENT:\nx\nEND_CONTENT",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert not (sandbox / "repo/tests/test_x.py").exists()
    assert not (tmp_path / "outside.py").exists()
    assert not (tmp_path / "secret.txt").exists()


@pytest.mark.skipif(not hasattr(Path, "symlink_to"), reason="Symlink unsupported")
def test_path_safety_rejects_symlink_escape_for_read_write(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo/src").mkdir(parents=True)
    try:
        (sandbox / "repo/src/link").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in this environment")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    responses = [
        "ACTION: read_file\nPATH: src/link/secret.txt",
        "ACTION: write_file\nPATH: src/link/secret.txt\nCONTENT:\nhacked\nEND_CONTENT",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert (outside / "secret.txt").read_text(encoding="utf-8") == "secret"


def test_finish_after_write_requires_visible_verification(tmp_path: Path):
    responses = [
        "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\nDEFAULT_RETRIES=3\nEND_CONTENT",
        "ACTION: finish\nREASON: done",
        "ACTION: run_tests",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES=5\n", encoding="utf-8")
    (sandbox / "tests/visible").mkdir(parents=True)
    (sandbox / "tests/visible/test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    err = (out / "runner_stderr.txt").read_text(encoding="utf-8")
    assert res.runner_crashed is False
    assert "finish blocked repeatedly" not in err


def test_finish_after_replace_text_requires_visible_verification(tmp_path: Path):
    responses = [
        "ACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDEFAULT_RETRIES=5\nEND_OLD\nNEW:\nDEFAULT_RETRIES=3\nEND_NEW",
        "ACTION: finish\nREASON: done",
        "ACTION: run_tests",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES=5\n", encoding="utf-8")
    (sandbox / "tests/visible").mkdir(parents=True)
    (sandbox / "tests/visible/test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    err = (out / "runner_stderr.txt").read_text(encoding="utf-8")
    assert res.runner_crashed is False
    assert "finish blocked repeatedly" not in err


def test_replace_text_rejects_ambiguous_and_missing(tmp_path: Path):
    def check_ambiguous(obs: str) -> None:
        assert "OLD text is ambiguous and occurs multiple times." in obs

    def check_missing(obs: str) -> None:
        assert "OLD text not found." in obs

    responses = [
        "ACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDEFAULT_RETRIES=5\nEND_OLD\nNEW:\nDEFAULT_RETRIES=3\nEND_NEW",
        "ACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDOES_NOT_EXIST\nEND_OLD\nNEW:\nDEFAULT_RETRIES=3\nEND_NEW",
        "ACTION: finish\nREASON: done",
    ]
    client = ObservationCheckingChatClient(responses, [check_ambiguous, check_missing])
    adapter = MinimalReactControlAdapter(chat_client=client)
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES=5\nDEFAULT_RETRIES=5\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, client, sandbox, out)


def test_replace_text_rejects_tests_and_outside_path(tmp_path: Path):
    responses = [
        "ACTION: replace_text\nPATH: tests/test_x.py\nOLD:\na\nEND_OLD\nNEW:\nb\nEND_NEW",
        "ACTION: replace_text\nPATH: ../outside.txt\nOLD:\na\nEND_OLD\nNEW:\nb\nEND_NEW",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert not (sandbox / "repo/tests/test_x.py").exists()
    assert not (tmp_path / "outside.txt").exists()


def test_finish_after_write_repeated_without_verification_crashes(tmp_path: Path):
    responses = [
        "ACTION: write_file\nPATH: src/demo_cli/config.py\nCONTENT:\nDEFAULT_RETRIES=3\nEND_CONTENT",
        "ACTION: finish\nREASON: done",
        "ACTION: finish\nREASON: done",
        "ACTION: finish\nREASON: done",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES=5\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    err = (out / "runner_stderr.txt").read_text(encoding="utf-8")
    assert res.runner_crashed is True
    assert "finish blocked repeatedly" in err


def test_finish_without_writes_is_allowed(tmp_path: Path):
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: finish\nREASON: no edits"]))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert res.runner_crashed is False


def test_minimal_control_requires_base_url_cli():
    with pytest.raises(SystemExit, match="minimal_react_control requires --base-url because it is model-backed."):
        main([
            "run",
            "--suite",
            "suites/core_v0_1",
            "--runner",
            "minimal_react_control",
            "--model",
            "dummy",
            "--output-dir",
            "artifacts/runs/control_dummy",
        ])


def test_list_files_ignores_generated_artifacts(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/__pycache__").mkdir(parents=True)
    (sandbox / "repo/src/app.py").write_text("print('ok')\n", encoding="utf-8")
    (sandbox / "repo/src/__pycache__/app.cpython.pyc").write_bytes(b"cached")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")

    def _check(obs: str) -> None:
        assert "src/app.py" in obs
        assert "__pycache__" not in obs
        assert ".pyc" not in obs

    client = ObservationCheckingChatClient(["ACTION: list_files\nPATH: .", "ACTION: finish\nREASON: done"], [_check])
    adapter = MinimalReactControlAdapter(chat_client=client)
    _run_adapter(adapter, client, sandbox, out)


def test_search_ignores_generated_artifacts(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/__pycache__").mkdir(parents=True)
    (sandbox / "repo/src/app.py").write_text("ACTIVE_TOKEN='real'\n", encoding="utf-8")
    (sandbox / "repo/src/__pycache__/cache.pyc").write_text("SECRET_ONLY_IN_CACHE", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")

    def _check(obs: str) -> None:
        assert "SECRET_ONLY_IN_CACHE" not in obs
        assert "(no matches)" in obs

    client = ObservationCheckingChatClient(["ACTION: search\nQUERY: SECRET_ONLY_IN_CACHE", "ACTION: finish\nREASON: done"], [_check])
    adapter = MinimalReactControlAdapter(chat_client=client)
    _run_adapter(adapter, client, sandbox, out)


def test_control_trace_written_with_action_and_observation(tmp_path: Path):
    responses = ["ACTION: list_files\nPATH: .", "ACTION: finish\nREASON: done"]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "repo/src/app.py").write_text("print('ok')\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    trace = out / "control_trace.jsonl"
    assert trace.exists()
    lines = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["model_output"].startswith("ACTION: list_files")
    assert lines[0]["parsed_action"] == "list_files"
    assert "src/app.py" in lines[0]["tool_result"]
    assert "tests/hidden" not in trace.read_text(encoding="utf-8")


def test_control_trace_logs_invalid_action(tmp_path: Path):
    responses = ["hello", "ACTION: finish\nREASON: done"]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    lines = [json.loads(line) for line in (out / "control_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[0]["valid_action"] is False
    assert lines[0]["parsed_action"] is None
    assert lines[0]["error"] == "missing_action"


def test_repeated_list_files_loop_crashes_with_note(tmp_path: Path):
    responses = ["ACTION: list_files\nPATH: ."] * 6
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert res.runner_crashed is True
    assert res.notes and "repeated identical actions" in res.notes
    lines = [json.loads(line) for line in (out / "control_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    blocked = [line for line in lines if line.get("error") == "blocked_repeated_action"]
    assert blocked
    assert blocked[0]["parsed_action"] == "list_files"
    assert blocked[0]["valid_action"] is True


def test_repeat_recovery_can_continue_to_success(tmp_path: Path):
    responses = [
        "ACTION: list_files\nPATH: .",
        "ACTION: list_files\nPATH: .",
        "ACTION: search\nQUERY: DEFAULT_RETRIES",
        "ACTION: read_file\nPATH: src/demo_cli/config.py",
        "ACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDEFAULT_RETRIES=5\nEND_OLD\nNEW:\nDEFAULT_RETRIES=3\nEND_NEW",
        "ACTION: run_tests",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES=5\n", encoding="utf-8")
    (sandbox / "tests/visible").mkdir(parents=True)
    (sandbox / "tests/visible/test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert res.runner_crashed is False


def test_invalid_then_valid_action_executes(tmp_path: Path):
    responses = [
        "I should inspect the repo.",
        "No action yet.",
        "\n\nACTION: list_files\nPATH: .",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "repo/src/app.py").write_text("print('ok')\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    res = _run_adapter(adapter, adapter._chat_client, sandbox, out)
    assert res.runner_crashed is False
    lines = [json.loads(line) for line in (out / "control_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[2]["parsed_action"] == "list_files"
    assert lines[2]["valid_action"] is True
    assert "src/app.py" in lines[2]["tool_result"]


def test_parse_action_tolerates_whitespace_and_preamble():
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: finish\nREASON: done"]))
    action, fields, error = adapter._parse_action("Looking at this task.\n\n  ACTION:list_files\n PATH : .\n")
    assert error is None
    assert action == "list_files"
    assert fields["PATH"] == "."


def test_parse_action_rejects_multiple_action_blocks():
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: finish\nREASON: done"]))
    action, fields, error = adapter._parse_action("ACTION: list_files\nPATH: .\n\nACTION: read_file\nPATH: src/a.py\n")
    assert action is None
    assert fields == {}
    assert error == "multiple_action_blocks"


def test_parse_action_preserves_replace_text_blocks_with_preamble():
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: finish\nREASON: done"]))
    action, fields, error = adapter._parse_action(
        "I found the constant.\n\nACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDEFAULT_RETRIES = 5\nEND_OLD\nNEW:\nDEFAULT_RETRIES = 3\nEND_NEW"
    )
    assert error is None
    assert action == "replace_text"
    assert fields["OLD"] == "DEFAULT_RETRIES = 5"
    assert fields["NEW"] == "DEFAULT_RETRIES = 3"


def test_parse_action_invalid_replace_text_delimiter_is_rejected():
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(["ACTION: finish\nREASON: done"]))
    action, fields, error = adapter._parse_action(
        "ACTION: replace_text\nPATH: src/demo_cli/config.py\nOLD:\nDEFAULT_RETRIES = 5\nNEW:\nDEFAULT_RETRIES = 3\nEND_NEW"
    )
    assert action is None
    assert fields == {}
    assert error == "missing_end_old"


def test_action_with_preamble_is_valid_in_trace(tmp_path: Path):
    responses = [
        "Looking at the task, I should inspect the repo.\n\nACTION: list_files\nPATH: .",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    lines = [json.loads(line) for line in (out / "control_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[0]["parsed_action"] == "list_files"
    assert lines[0]["valid_action"] is True


def test_run_tests_ignores_extra_path_fields(tmp_path: Path):
    responses = [
        "ACTION: run_tests\nPATH: tests/visible",
        "ACTION: run_tests\nPATH: .",
        "ACTION: finish\nREASON: done",
    ]
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "tests/visible").mkdir(parents=True)
    (sandbox / "tests/visible/test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, adapter._chat_client, sandbox, out)
    lines = [json.loads(line) for line in (out / "control_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[0]["parsed_action"] == "run_tests"
    assert lines[0]["valid_action"] is True
    assert lines[1]["parsed_action"] == "run_tests"
    assert "tests/hidden" not in (out / "control_trace.jsonl").read_text(encoding="utf-8")


def test_max_model_calls_sets_budget_exceeded_note(tmp_path: Path):
    responses = ["ACTION: list_files\nPATH: ."] * 5
    adapter = MinimalReactControlAdapter(chat_client=ScriptedChatClient(responses))
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    budget = BudgetProfile(120, 2, 100, 100, 10, 10, 10, 10, 4096, 0)
    res = adapter.run(VB_MIN_001, sandbox, budget, {"task_output_dir": str(out), "model": "dummy", "base_url": "http://localhost"})
    assert res.budget_exceeded is True
    assert res.notes and "max_model_calls" in res.notes


def test_system_prompt_contains_workflow_and_no_hidden_paths(tmp_path: Path):
    client = PromptCaptureClient()
    adapter = MinimalReactControlAdapter(chat_client=client)
    sandbox = tmp_path / "sandbox"
    out = tmp_path / "out"
    out.mkdir()
    (sandbox / "repo/src").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("fix", encoding="utf-8")
    _run_adapter(adapter, client, sandbox, out)
    prompt = client.system_prompt
    assert "Use this default workflow" in prompt
    assert "Do not assume hidden tests." in prompt
    assert "tests/hidden" not in prompt
    assert "oracle" not in prompt.lower()
