import json
from pathlib import Path

from villanibench.harness.adapters import build_adapter
from villanibench.harness.adapters.pi import PiAdapter, _normalise_base_url
from villanibench.harness.budget import get_budget_profile


class T:
    visible_test_command = "pytest tests/visible"


def _sandbox(tmp_path: Path) -> Path:
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    return sandbox


def test_get_adapter_pi():
    assert isinstance(build_adapter("pi"), PiAdapter)


def test_base_url_normalization():
    assert _normalise_base_url("http://127.0.0.1:1234") == "http://127.0.0.1:1234/v1"
    assert _normalise_base_url("http://127.0.0.1:1234/v1") == "http://127.0.0.1:1234/v1"


def test_pi_writes_models_json_and_env_and_argv_with_base_url(monkeypatch, tmp_path: Path):
    sandbox = _sandbox(tmp_path)
    prompt = 'a "quoted" prompt\n$HOME `echo` C:\\tmp\\x'
    (sandbox / "prompt.txt").write_text(prompt, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["argv"] = argv
        seen["cwd"] = cwd
        seen["env"] = env or {}

        class R:
            exit_code = 0
            stdout = '{"event":"ok"}\n'
            stderr = ""
            timed_out = False

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.pi.run_command_tree_argv", _fake_run)

    adapter = PiAdapter()
    res = adapter.run(
        T(),
        sandbox,
        get_budget_profile("lite_v0_1"),
        {
            "task_output_dir": str(out),
            "model": "zai-org/GLM-5.1",
            "base_url": "http://127.0.0.1:1234",
            "api_key": "dummy",
            "pi_path": "pi",
        },
    )

    assert res.exit_code == 0
    models_path = sandbox / ".pi-agent" / "agent" / "models.json"
    assert models_path.exists()
    data = json.loads(models_path.read_text(encoding="utf-8"))
    provider = data["providers"]["villani-local"]
    assert provider["baseUrl"] == "http://127.0.0.1:1234/v1"
    assert provider["api"] == "openai-completions"
    assert provider["apiKey"] == "VILLANI_PI_API_KEY"
    assert provider["models"][0]["id"] == "zai-org/GLM-5.1"
    assert str(models_path).startswith(str(sandbox))

    env = seen["env"]
    assert env["PI_CODING_AGENT_DIR"] == str((sandbox / ".pi-agent").resolve())
    assert env["PI_CODING_AGENT_SESSION_DIR"] == str((sandbox / ".pi-sessions").resolve())
    assert env["VILLANI_PI_API_KEY"] == "dummy"

    argv = seen["argv"]
    assert argv[0] == "pi"
    assert "--mode" in argv and "json" in argv
    assert "--no-session" in argv
    assert "--provider" in argv and "villani-local" in argv
    assert argv[argv.index("--model") + 1] == "zai-org/GLM-5.1"
    assert argv[-1] == prompt


def test_pi_argv_without_base_url_has_no_provider(monkeypatch, tmp_path: Path):
    sandbox = _sandbox(tmp_path)
    prompt = "hello world"
    (sandbox / "prompt.txt").write_text(prompt, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["argv"] = argv

        class R:
            exit_code = 0
            stdout = ""
            stderr = ""
            timed_out = False

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.pi.run_command_tree_argv", _fake_run)
    adapter = PiAdapter()
    adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m", "pi_path": "pi"})

    assert "--provider" not in seen["argv"]


def test_pi_timeout_bubbles(monkeypatch, tmp_path: Path):
    sandbox = _sandbox(tmp_path)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        class R:
            exit_code = 124
            stdout = ""
            stderr = "timeout"
            timed_out = True

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.pi.run_command_tree_argv", _fake_run)
    adapter = PiAdapter()
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m", "pi_path": "pi"})
    assert res.timed_out is True
