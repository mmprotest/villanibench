from villanibench.harness.scoring import aggregate_overall_paired, aggregate_paired_scores


def _rows(control_statuses, runner_statuses, model="m1", control_kind="model_backed"):
    out=[]
    for i,(c,r) in enumerate(zip(control_statuses, runner_statuses), start=1):
        base={"model":model,"suite_id":"s","comparison_mode":"strict","budget_profile":"b","task_id":f"t{i}","run_id":"x"}
        out.append({**base,"runner":"minimal_react_control","status":c,"control_kind":control_kind})
        out.append({**base,"runner":"villani","status":r})
    return out


def test_runner_beats_control_plus_50():
    rows=_rows(["visible_failure","success"],["success","success"])
    by,_=aggregate_paired_scores(rows)
    assert by[0]["villanibench_score"]==50.0


def test_runner_loses_control_minus_50():
    rows=_rows(["success","success"],["visible_failure","success"])
    by,_=aggregate_paired_scores(rows)
    assert by[0]["villanibench_score"]==-50.0


def test_ties_zero():
    rows=_rows(["success","visible_failure"],["success","visible_failure"])
    by,_=aggregate_paired_scores(rows)
    assert by[0]["villanibench_score"]==0.0


def test_missing_control_not_computed():
    rows=[{"run_id":"r","runner":"villani","model":"m","task_id":"t","suite_id":"s","budget_profile":"b","comparison_mode":"strict","status":"success"}]
    by,_=aggregate_paired_scores(rows)
    assert by[0]["score_validity"]=="not_computed"


def test_non_model_backed_control_not_computed():
    rows=_rows(["success"],["success"],control_kind="placeholder")
    by,_=aggregate_paired_scores(rows)
    assert by[0]["score_validity"]=="not_computed"


def test_duplicate_rows_fail():
    rows=_rows(["success"],["success"])
    rows.append(rows[-1].copy())
    import pytest
    with pytest.raises(ValueError):
        aggregate_paired_scores(rows)


def test_bootstrap_ci_contains_score():
    rows=_rows(["visible_failure","success","visible_failure","success"],["success","success","visible_failure","success"])
    by,_=aggregate_paired_scores(rows)
    overall=aggregate_overall_paired(by, iterations=200, seed=0)[0]
    assert overall["score_ci_low"] <= overall["villanibench_score"] <= overall["score_ci_high"]
    assert overall["ci_method"]=="task_bootstrap"
