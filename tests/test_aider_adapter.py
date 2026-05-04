import json
from pathlib import Path

from villanibench.harness.adapters import build_adapter
from villanibench.harness.adapters.aider import AiderAdapter, _safe_expected_files, normalize_aider_model
from villanibench.harness.budget import get_budget_profile


class T:
    visible_test_command = "pytest tests/visible -q"

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir


def _sandbox(tmp_path: Path) -> tuple[Path, Path, Path]:
    sandbox = tmp_path / "sandbox"
    repo = sandbox / "repo"
    repo.mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("Fix bug", encoding="utf-8")
    task_dir = tmp_path / "task"
    (task_dir / "oracle").mkdir(parents=True)
    return sandbox, repo, task_dir


def test_registration():
    assert isinstance(build_adapter("aider"), AiderAdapter)


def test_model_normalization():
    assert normalize_aider_model("qwen3.5-coder") == "openai/qwen3.5-coder"
    assert normalize_aider_model("openai/qwen3.5-coder") == "openai/qwen3.5-coder"


def test_expected_file_filtering(tmp_path: Path):
    sandbox, repo, task_dir = _sandbox(tmp_path)
    (repo / "ok.py").write_text("x=1\n", encoding="utf-8")
    (repo / "dir").mkdir()
    payload = {
        "expected_files": ["ok.py", "/abs.py", "../outside.py", "missing.py", "dir"],
        "strongly_expected_files": [],
    }
    (task_dir / "oracle" / "expected_files.json").write_text(json.dumps(payload), encoding="utf-8")
    filtered = _safe_expected_files(T(task_dir), repo)
    assert filtered == ["ok.py"]


def test_command_and_redaction_and_timeout(monkeypatch, tmp_path: Path):
    sandbox, repo, task_dir = _sandbox(tmp_path)
    (repo / "target.py").write_text("pass\n", encoding="utf-8")
    (task_dir / "oracle" / "expected_files.json").write_text(
        json.dumps({"expected_files": ["target.py"]}), encoding="utf-8"
    )

    seen = {}

    def _fake_run(argv, cwd, timeout_sec, env=None, stdin_text=None):
        seen["argv"] = argv
        seen["env"] = env or {}

        class R:
            exit_code = 124
            stdout = "partial"
            stderr = "timeout"
            timed_out = True
            wall_time_sec = 1.0

        return R()

    monkeypatch.setattr("villanibench.harness.adapters.aider.run_command_tree_argv", _fake_run)

    out = tmp_path / "out"
    out.mkdir()
    res = AiderAdapter().run(
        T(task_dir),
        sandbox,
        get_budget_profile("lite_v0_1"),
        {
            "task_output_dir": str(out),
            "model": "qwen3.5-coder",
            "base_url": "http://127.0.0.1:1234/v1",
            "api_key": "secret-key",
        },
    )

    assert res.timed_out is True
    argv = seen["argv"]
    assert "--message-file" in argv
    assert "--yes-always" in argv
    assert "--no-auto-commits" in argv
    assert "--no-dirty-commits" in argv
    assert "--openai-api-base" in argv
    assert "--openai-api-key" in argv
    assert "--no-auto-test" in argv
    assert "--no-auto-lint" in argv

    cmd = json.loads((out / "aider_command.json").read_text(encoding="utf-8"))
    assert "secret-key" not in json.dumps(cmd)
    assert "<redacted>" in json.dumps(cmd)
