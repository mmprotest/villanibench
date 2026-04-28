import json
from pathlib import Path

import pytest

from villanibench.cli import main
from villanibench.harness.adapters.minimal_react_control import MinimalReactControlAdapter
from villanibench.harness.llm import ChatMessage, ChatResponse
from villanibench.harness.run import run_suite


SUITE_DIR = Path("suites/core_v0_1")


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
