import json
from pathlib import Path

from villanibench.cli import main
from villanibench.harness.compare import compare_runs


def _write_rows(run_dir: Path, rows: list[dict]) -> None:
    run_dir.mkdir()
    (run_dir / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_per_model_and_overall_pooling(tmp_path: Path):
    base={"suite_id":"s","comparison_mode":"strict","budget_profile":"b","task_id":"t1","run_id":"r"}
    _write_rows(tmp_path/"c1", [{**base,"runner":"minimal_react_control","model":"A","status":"visible_failure","control_kind":"model_backed"},{**base,"task_id":"t2","runner":"minimal_react_control","model":"A","status":"success","control_kind":"model_backed"}])
    _write_rows(tmp_path/"r1", [{**base,"runner":"villani","model":"A","status":"success"},{**base,"task_id":"t2","runner":"villani","model":"A","status":"success"}])
    _write_rows(tmp_path/"c2", [{**base,"runner":"minimal_react_control","model":"B","status":"success","control_kind":"model_backed"},{**base,"task_id":"t2","runner":"minimal_react_control","model":"B","status":"success","control_kind":"model_backed"}])
    _write_rows(tmp_path/"r2", [{**base,"runner":"villani","model":"B","status":"success"},{**base,"task_id":"t2","runner":"villani","model":"B","status":"success"}])
    summary=compare_runs([tmp_path/"c1",tmp_path/"r1",tmp_path/"c2",tmp_path/"r2"], tmp_path/"out")
    overall=summary["villanibench_scores_overall"][0]
    assert overall["model_count"]==2
    assert overall["paired_task_count"]==4
    assert overall["villanibench_score"]==25.0


def test_pooled_score_cli_and_outputs(tmp_path: Path):
    rows=[{"run_id":"x","runner":"minimal_react_control","model":"A","suite_id":"s","budget_profile":"b","comparison_mode":"strict","task_id":"t","status":"visible_failure","control_kind":"model_backed"},
          {"run_id":"y","runner":"villani","model":"A","suite_id":"s","budget_profile":"b","comparison_mode":"strict","task_id":"t","status":"success"}]
    _write_rows(tmp_path/"c", [rows[0]])
    _write_rows(tmp_path/"r", [rows[1]])
    main(["score", str(tmp_path/"c"), str(tmp_path/"r"), "--output-dir", str(tmp_path/"scoreout")])
    summary=json.loads((tmp_path/"scoreout/pooled_score_summary.json").read_text())
    assert (tmp_path/"scoreout/pooled_score_report.md").exists()
    assert summary["scoring_method"]=="paired_control_adjusted_net_success_v1"


def test_pooled_warns_incomplete_metadata(tmp_path: Path):
    _write_rows(tmp_path/"bad", [{"runner":"villani","task_id":"t","status":"success"}])
    summary=compare_runs([tmp_path/"bad"], tmp_path/"out2")
    assert summary["excluded_row_count"]==1
    assert any("missing fields" in w for w in summary["warnings"])
