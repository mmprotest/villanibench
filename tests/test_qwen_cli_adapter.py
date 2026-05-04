import json
from pathlib import Path

from villanibench.harness.adapters import build_adapter
from villanibench.harness.adapters.qwen_cli import QwenCliAdapter, _normalise_base_url, parse_qwen_output
from villanibench.harness.budget import get_budget_profile


class T:
    prompt = "Fix the bug"
    visible_test_command = "pytest tests/visible -q"


def _sandbox(tmp_path: Path) -> Path:
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    return sandbox


def test_get_adapter_qwen_cli():
    assert isinstance(build_adapter("qwen-cli"), QwenCliAdapter)


def test_base_url_normalization_qwen():
    assert _normalise_base_url("http://127.0.0.1:1234") == "http://127.0.0.1:1234/v1"
    assert _normalise_base_url("http://127.0.0.1:1234/v1") == "http://127.0.0.1:1234/v1"


def test_missing_executable_errors_cleanly(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("villanibench.harness.adapters.qwen_cli.shutil.which", lambda _x: None)
    sandbox = _sandbox(tmp_path)
    out = tmp_path / "out"
    out.mkdir()

    adapter = QwenCliAdapter()
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m", "base_url": "http://x/v1"})
    assert res.exit_code == 1
    err = (out / "qwen_cli_stderr.txt").read_text(encoding="utf-8")
    assert "Qwen Code CLI executable not found" in err


def test_qwen_writes_settings_and_argv_and_env(monkeypatch, tmp_path: Path):
    sandbox = _sandbox(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    monkeypatch.setattr("villanibench.harness.adapters.qwen_cli._resolve_qwen_executable", lambda: "/usr/bin/qwen")

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["argv"] = argv
        seen["cwd"] = cwd
        seen["env"] = env or {}

        class R:
            exit_code = 0
            stdout = '[{"type":"message"},{"type":"result","ok":true}]'
            stderr = ""
            timed_out = False
            wall_time_sec = 0.1

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.qwen_cli.run_command_tree_argv", _fake_run)

    adapter = QwenCliAdapter()
    adapter.run(
        T(),
        sandbox,
        get_budget_profile("lite_v0_1"),
        {
            "task_output_dir": str(out),
            "model": "exact-model-id",
            "base_url": "http://127.0.0.1:1234/v1",
            "api_key": "super-secret",
        },
    )

    settings_path = sandbox / "repo" / ".qwen" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    provider = settings["modelProviders"]["openai"][0]
    assert provider["id"] == "exact-model-id"
    assert settings["model"]["name"] == "exact-model-id"
    assert provider["baseUrl"] == "http://127.0.0.1:1234/v1"
    assert "super-secret" not in settings_path.read_text(encoding="utf-8")

    assert seen["env"]["VILLANIBENCH_QWEN_API_KEY"] == "super-secret"
    argv = seen["argv"]
    assert argv[0] == "/usr/bin/qwen"
    assert "--prompt" in argv
    assert "--output-format" in argv and "json" in argv
    assert "--approval-mode" in argv and "yolo" in argv
    assert argv[argv.index("--model") + 1] == "exact-model-id"


def test_parse_qwen_output_valid_and_invalid():
    ok = parse_qwen_output('[{"type":"x"},{"type":"result","a":1}]')
    assert ok["result"]["a"] == 1
    bad = parse_qwen_output('not-json')
    assert "json_parse_error" in bad


def test_qwen_timeout_bubbles(monkeypatch, tmp_path: Path):
    sandbox = _sandbox(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr("villanibench.harness.adapters.qwen_cli._resolve_qwen_executable", lambda: "qwen")

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        class R:
            exit_code = 124
            stdout = ""
            stderr = "timeout"
            timed_out = True
            wall_time_sec = 1.0

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.qwen_cli.run_command_tree_argv", _fake_run)
    res = QwenCliAdapter().run(
        T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m", "base_url": "http://x/v1"}
    )
    assert res.timed_out is True
