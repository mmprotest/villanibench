from pathlib import Path

from villanibench.harness.adapters.claude_code import ClaudeCodeAdapter
from villanibench.harness.budget import get_budget_profile


class T:
    visible_test_command = "pytest tests/visible"


def test_claude_code_uses_argv_and_permission_bypass(monkeypatch, tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("hello", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    seen = {}

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["argv"] = argv
        seen["cwd"] = cwd
        seen["env"] = env or {}
        seen["stdin_text"] = stdin_text

        class R:
            exit_code = 0
            stdout = "ok"
            stderr = ""
            timed_out = False

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.claude_code.run_command_tree_argv", _fake_run)

    adapter = ClaudeCodeAdapter()
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})

    assert res.exit_code == 0
    assert seen["argv"][:3] == ["claude", "-p", "--dangerously-skip-permissions"]
    assert "<" not in " ".join(seen["argv"])
    assert seen["stdin_text"] == "hello"


def test_claude_code_sets_anthropic_env_vars(monkeypatch, tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    seen = {}

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["env"] = env or {}

        class R:
            exit_code = 0
            stdout = ""
            stderr = ""
            timed_out = False

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.claude_code.run_command_tree_argv", _fake_run)

    adapter = ClaudeCodeAdapter()
    adapter.run(
        T(),
        sandbox,
        get_budget_profile("lite_v0_1"),
        {
            "task_output_dir": str(out),
            "model": "m",
            "base_url": "http://localhost:1234/v1",
            "api_key": "secret-token",
        },
    )

    env = seen["env"]
    assert env["ANTHROPIC_BASE_URL"] == "http://localhost:1234/v1"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "secret-token"
    assert env["ANTHROPIC_API_KEY"] == "secret-token"

    command_text = (out / "runner_command.txt").read_text(encoding="utf-8")
    assert "secret-token" not in command_text
    assert "ANTHROPIC_AUTH_TOKEN=<redacted>" in command_text
