import subprocess

from pathlib import Path

from villanibench.harness.adapters.external_cli import ExternalCliAdapter
from villanibench.harness.budget import get_budget_profile


class T:
    visible_test_command = "pytest tests/visible"


def test_external_cli_runs_fake_command_and_substitutes(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo/src/demo_cli").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("hello", encoding="utf-8")
    cfg = sandbox / "repo/src/demo_cli/config.py"
    cfg.write_text("DEFAULT_RETRIES = 5\n", encoding="utf-8")
    adapter = ExternalCliAdapter(
        "fake",
        "python -c \"from pathlib import Path; p=Path('src/demo_cli/config.py'); p.write_text(p.read_text().replace('DEFAULT_RETRIES = 5', 'DEFAULT_RETRIES = 3'))\"",
    )
    out = tmp_path / "out"
    out.mkdir()
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {
        "task_output_dir": str(out), "model": "m", "base_url": "u", "api_key": "k"
    })
    assert res.exit_code == 0
    assert "DEFAULT_RETRIES = 3" in cfg.read_text(encoding="utf-8")


def test_missing_cli_is_runner_crash(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", "definitely_missing_command_zz")
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.runner_crashed is True


def test_timeout_reported(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", "python -c \"import time; time.sleep(2)\"")
    b = get_budget_profile("lite_v0_1")
    object.__setattr__(b, "wall_time_sec", 1)
    res = adapter.run(T(), sandbox, b, {"task_output_dir": str(out), "model": "m"})
    assert res.timed_out is True


def test_external_cli_sets_utf8_env(tmp_path: Path, monkeypatch):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    seen = {}

    def _fake_run_command_tree(command, cwd, timeout_sec, env=None):
        seen["env"] = env or {}
        class R:
            exit_code = 0
            stdout = ""
            stderr = ""
            timed_out = False
        return R()

    monkeypatch.setattr("villanibench.harness.adapters.external_cli.run_command_tree", _fake_run_command_tree)
    adapter = ExternalCliAdapter("fake", "echo hi")
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.exit_code == 0
    assert seen["env"].get("PYTHONIOENCODING") == "utf-8"
    assert seen["env"].get("PYTHONUTF8") == "1"


def test_external_cli_usage_error_adds_note(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    (sandbox / "repo").mkdir(parents=True)
    (sandbox / "prompt.txt").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    adapter = ExternalCliAdapter("fake", 'python -c "import sys; print(\'No such option: --prompt-file\', file=sys.stderr); sys.exit(2)"')
    res = adapter.run(T(), sandbox, get_budget_profile("lite_v0_1"), {"task_output_dir": str(out), "model": "m"})
    assert res.runner_crashed is True
    assert res.notes is not None
    assert "External runner command appears invalid" in res.notes
