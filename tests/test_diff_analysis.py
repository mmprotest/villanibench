import json
from pathlib import Path

from villanibench.harness.diff_analysis import analyze_diff, snapshot_files


def test_diff_analysis_detects_changed_files(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "repo/src/demo_cli").mkdir(parents=True)
    (root / "tests/visible").mkdir(parents=True)
    (root / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES = 5\n", encoding="utf-8")

    task_dir = tmp_path / "task"
    (task_dir / "oracle").mkdir(parents=True)
    (task_dir / "oracle/allowed_files.json").write_text(json.dumps({"forbidden_patterns": ["tests/"]}), encoding="utf-8")
    (task_dir / "oracle/expected_files.json").write_text(json.dumps({"expected_files": ["src/demo_cli/config.py"]}), encoding="utf-8")
    (task_dir / "oracle/failure_modes.json").write_text("{}", encoding="utf-8")

    before = snapshot_files(root)
    (root / "repo/src/demo_cli/config.py").write_text("DEFAULT_RETRIES = 3\n", encoding="utf-8")
    stats = analyze_diff(before, snapshot_files(root), root, task_dir, tmp_path / "final.diff")
    assert "repo/src/demo_cli/config.py" in stats.files_touched
