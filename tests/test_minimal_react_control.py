import json
from pathlib import Path
from typing import Callable

import pytest

from villanibench.cli import main
from villanibench.harness.adapters.minimal_react_control import MinimalReactControlAdapter
from villanibench.harness.budget import get_budget_profile
from villanibench.harness.llm import ChatMessage, ChatResponse
from villanibench.harness.run import run_suite
from villanibench.tasks.loader import load_task


SUITE_DIR = Path("suites/core_v0_1")
VB_MIN_001 = load_task(SUITE_DIR / "tasks" / "VB-MIN-001")


class FakeChatClient:
    def __init__(self):
        self.calls = 0

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        self.calls += 1
        joined = "\n".join(m.content for m in messages)
        assert "tests/hidden" not in joined
        if self.calls == 1:
            return ChatResponse("ACTION: read_file\nPATH: src/demo_cli/config.py", prompt_tokens=10, completion_tokens=8)
        if self.calls == 2:
            content = (
                "ACTION: write_file\n"
                "PATH: src/demo_cli/config.py\n"
                "CONTENT:\n"
                '"""Config constants for the demo CLI."""\n\nDEFAULT_RETRIES = 3\n'
                "END_CONTENT"
            )
            return ChatResponse(content, prompt_tokens=11, completion_tokens=10)
        if self.calls == 3:
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
