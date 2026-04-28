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


def test_compare_valid_score_with_model_backed_control(tmp_path: Path):
    control = tmp_path / "control"
    runner = tmp_path / "runner"
    base = {
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
    }
    _write_rows(control, [
        {**base, "runner": "minimal_react_control", "task_id": "t1", "control_kind": "model_backed", "status": "visible_failure"},
        {**base, "runner": "minimal_react_control", "task_id": "t2", "control_kind": "model_backed", "status": "success"},
    ])
    _write_rows(runner, [
        {**base, "runner": "villani", "task_id": "t1", "control_kind": None, "status": "success", "setting_warnings": []},
        {**base, "runner": "villani", "task_id": "t2", "control_kind": None, "status": "success", "setting_warnings": []},
    ])
    summary = compare_runs([control, runner], tmp_path / "out")
    row = summary["villanibench_scores_by_model"][0]
    assert row["score_validity"] == "valid"
    assert row["model_villanibench_score"] == 1.0
    assert summary["raw_scores"][1]["raw_solve_rate"] == 1.0


def test_compare_missing_control_is_not_computed(tmp_path: Path):
    runner = tmp_path / "runner"
    _write_rows(runner, [{
        "runner": "villani",
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
        "task_id": "VB-MIN-001",
        "status": "success",
        "control_kind": None,
        "setting_warnings": [],
    }])
    summary = compare_runs([runner], tmp_path / "out")
    assert summary["villanibench_scores_by_model"][0]["score_validity"] == "not_computed"
    assert any("No matching minimal_react_control run found" in w for w in summary["warnings"])


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


def test_compare_backend_stability_section(tmp_path: Path):
    control_a = tmp_path / "control_a"
    control_b = tmp_path / "control_b"
    runner_a = tmp_path / "runner_a"
    runner_b = tmp_path / "runner_b"
    base = {"suite_id": "s", "comparison_mode": "strict", "budget_profile": "b", "category": "minimal_patch"}
    _write_rows(control_a, [{**base, "runner": "minimal_react_control", "model": "m1", "task_id": "t", "control_kind": "model_backed", "status": "visible_failure"}])
    _write_rows(control_b, [{**base, "runner": "minimal_react_control", "model": "m2", "task_id": "t", "control_kind": "model_backed", "status": "visible_failure"}])
    _write_rows(runner_a, [{**base, "runner": "villani", "model": "m1", "task_id": "t", "control_kind": None, "status": "success", "setting_warnings": []}])
    _write_rows(runner_b, [{**base, "runner": "villani", "model": "m2", "task_id": "t", "control_kind": None, "status": "success", "setting_warnings": []}])
    summary = compare_runs([control_a, control_b, runner_a, runner_b], tmp_path / "out")
    overall = summary["villanibench_scores_overall"][0]
    assert overall["backend_stability_stddev"] is not None
    assert overall["stable"] is True


def test_report_includes_raw_diagnostics_when_no_valid_scores(tmp_path: Path):
    runner = tmp_path / "runner"
    _write_rows(runner, [{
        "runner": "villani",
        "model": "dummy",
        "suite_id": "villanibench-core-v0.1",
        "comparison_mode": "strict",
        "budget_profile": "lite_v0_1",
        "category": "minimal_patch",
        "task_id": "VB-MIN-001",
        "status": "success",
        "success_visible": True,
        "success_hidden": True,
        "forbidden_file_modified": False,
        "tests_modified": False,
        "control_kind": None,
        "setting_warnings": [],
    }])
    compare_runs([runner], tmp_path / "out")
    report = (tmp_path / "out/REPORT.md").read_text(encoding="utf-8")
    assert "No valid VillaniBench Score is available for this comparison. See raw diagnostics below." in report
    assert "## Raw solve-rate diagnostics" in report


def test_compare_raw_scores_do_not_mix_across_suites(tmp_path: Path):
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    _write_rows(run_a, [{
        "runner": "villani",
        "model": "dummy",
        "suite_id": "suite-a",
        "comparison_mode": "strict",
        "budget_profile": "standard_v0_1",
        "category": "minimal_patch",
        "task_id": "t1",
        "status": "success",
        "success_visible": True,
        "success_hidden": True,
        "forbidden_file_modified": False,
        "tests_modified": False,
        "setting_warnings": [],
    }])
    _write_rows(run_b, [{
        "runner": "villani",
        "model": "dummy",
        "suite_id": "suite-b",
        "comparison_mode": "strict",
        "budget_profile": "standard_v0_1",
        "category": "minimal_patch",
        "task_id": "t1",
        "status": "visible_failure",
        "success_visible": False,
        "success_hidden": False,
        "forbidden_file_modified": False,
        "tests_modified": False,
        "setting_warnings": [],
    }])
    summary = compare_runs([run_a, run_b], tmp_path / "out")
    idx = {(r["suite_id"], r["budget_profile"]): r for r in summary["raw_scores"]}
    assert idx[("suite-a", "standard_v0_1")]["raw_solve_rate"] == 1.0
    assert idx[("suite-b", "standard_v0_1")]["raw_solve_rate"] == 0.0


def test_compare_raw_scores_do_not_mix_across_budget_profiles_and_report_mapping(tmp_path: Path):
    control_std = tmp_path / "control_std"
    control_lite = tmp_path / "control_lite"
    runner_std = tmp_path / "runner_std"
    runner_lite = tmp_path / "runner_lite"
    base = {
        "runner": "villani",
        "model": "dummy",
        "suite_id": "suite-a",
        "comparison_mode": "strict",
        "category": "minimal_patch",
        "task_id": "t1",
        "control_kind": None,
        "setting_warnings": [],
    }
    _write_rows(control_std, [{"runner": "minimal_react_control", "model": "dummy", "suite_id": "suite-a", "comparison_mode": "strict", "budget_profile": "standard_v0_1", "category": "minimal_patch", "task_id": "t1", "status": "visible_failure", "control_kind": "model_backed"}])
    _write_rows(control_lite, [{"runner": "minimal_react_control", "model": "dummy", "suite_id": "suite-a", "comparison_mode": "strict", "budget_profile": "lite_v0_1", "category": "minimal_patch", "task_id": "t1", "status": "success", "control_kind": "model_backed"}])
    _write_rows(runner_std, [{**base, "budget_profile": "standard_v0_1", "status": "success"}])
    _write_rows(runner_lite, [{**base, "budget_profile": "lite_v0_1", "status": "visible_failure"}])

    summary = compare_runs([control_std, control_lite, runner_std, runner_lite], tmp_path / "out")
    raw_idx = {(r["suite_id"], r["budget_profile"], r["runner"]): r for r in summary["raw_scores"]}
    assert raw_idx[("suite-a", "standard_v0_1", "villani")]["raw_solve_rate"] == 1.0
    assert raw_idx[("suite-a", "lite_v0_1", "villani")]["raw_solve_rate"] == 0.0
    vb_idx = {(r["suite_id"], r["budget_profile"]): r for r in summary["villanibench_scores_by_model"]}
    assert vb_idx[("suite-a", "standard_v0_1")]["model_villanibench_score"] == 1.0
    assert vb_idx[("suite-a", "lite_v0_1")]["model_villanibench_score"] == -1.0
    report = (tmp_path / "out/REPORT.md").read_text(encoding="utf-8")
    assert "| villani | dummy | suite-a | standard_v0_1 | strict | valid | 1.000" in report
    assert "| villani | dummy | suite-a | lite_v0_1 | strict | valid | -1.000" in report
