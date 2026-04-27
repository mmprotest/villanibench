import json
from pathlib import Path

from villanibench.harness.adapters.external_cli import ExternalCliAdapter
from villanibench.harness.run import run_suite


SUITE_DIR = Path("suites/core_v0_1")


def test_hidden_tests_are_isolated_until_post_runner(tmp_path: Path, monkeypatch):
    adapter = ExternalCliAdapter(
        "fake_external",
        "python -c \"from pathlib import Path; import sys; sys.exit(1 if Path('../tests/hidden').exists() or Path('tests/hidden').exists() else 0)\"",
    )
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(SUITE_DIR, "fake_external", "dummy", out, {})

    task_dir = out / "tasks" / "VB-MIN-001"
    result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    assert result["runner_crashed"] is False
    assert (task_dir / "sandbox/tests/hidden").exists()


def test_external_fake_runner_end_to_end_fixes_task(tmp_path: Path, monkeypatch):
    adapter = ExternalCliAdapter(
        "fake_external",
        "python -c \"from pathlib import Path; p=Path('src/demo_cli/config.py'); p.write_text(p.read_text().replace('DEFAULT_RETRIES = 5', 'DEFAULT_RETRIES = 3'))\"",
    )
    monkeypatch.setattr("villanibench.harness.run.build_adapter", lambda _name: adapter)

    out = tmp_path / "run"
    run_suite(SUITE_DIR, "fake_external", "dummy", out, {})

    task_dir = out / "tasks" / "VB-MIN-001"
    result = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    diff_text = (task_dir / "final.diff").read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["success_visible"] is True
    assert result["success_hidden"] is True
    assert result["expected_file_touched"] is True
    assert result["tests_modified"] is False
    assert result["forbidden_file_modified"] is False
    assert result["patch_size_lines"] <= 4
    assert "DEFAULT_RETRIES = 5" in diff_text
    assert "DEFAULT_RETRIES = 3" in diff_text
    assert "tests/hidden" not in diff_text
