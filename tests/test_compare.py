import json
from pathlib import Path

from villanibench.harness.compare import compare_runs


def test_compare_combines_fake_runs(tmp_path: Path):
    run = tmp_path / "run1"
    run.mkdir()
    row = {
        "runner": "minimal_react_control",
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "non_strict",
        "category": "minimal_patch",
        "status": "visible_failure",
        "task_id": "VB-MIN-001",
    }
    (run / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    summary = compare_runs([run], tmp_path / "out")
    assert summary["raw_scores"]
    assert (tmp_path / "out" / "REPORT.md").exists()
