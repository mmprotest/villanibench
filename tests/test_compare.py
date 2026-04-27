import json
from pathlib import Path

from villanibench.harness.compare import compare_runs


def _write_rows(run_dir: Path, rows: list[dict]) -> None:
    run_dir.mkdir()
    (run_dir / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_compare_marks_placeholder_score_diagnostic_only(tmp_path: Path):
    control = tmp_path / "control"
    runner = tmp_path / "runner"
    base = {
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "non_strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
        "task_id": "VB-MIN-001",
    }
    _write_rows(control, [{**base, "runner": "minimal_react_control", "control_kind": "placeholder", "status": "visible_failure"}])
    _write_rows(runner, [{**base, "runner": "external", "control_kind": None, "status": "success", "setting_warnings": []}])

    summary = compare_runs([control, runner], tmp_path / "out")
    assert summary["villanibench_scores_by_model"][0]["score_validity"] == "diagnostic_only"
    report = (tmp_path / "out/REPORT.md").read_text(encoding="utf-8")
    assert "diagnostic only" in report


def test_compare_warns_on_strict_mode_mismatch(tmp_path: Path):
    control = tmp_path / "control"
    runner = tmp_path / "runner"
    _write_rows(control, [{
        "runner": "minimal_react_control",
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "non_strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
        "task_id": "VB-MIN-001",
        "status": "visible_failure",
        "control_kind": "placeholder",
    }])
    _write_rows(runner, [{
        "runner": "external",
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
        "task_id": "VB-MIN-001",
        "status": "success",
        "control_kind": None,
        "setting_warnings": ["base_url_not_used_by_template"],
    }])

    summary = compare_runs([control, runner], tmp_path / "out")
    assert any("comparison_mode=strict" in w for w in summary["warnings"])
    assert "base_url_not_used_by_template" in summary["warnings"]
    assert summary["villanibench_scores_by_model"][0]["score_validity"] == "not_computed"
