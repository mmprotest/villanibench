from villanibench.harness.scoring import aggregate_model_category_scores, villanibench_category_score


def test_scoring_equal_zero():
    assert villanibench_category_score(0.4, 0.4) == 0.0


def test_scoring_positive():
    assert round(villanibench_category_score(0.30, 0.51), 2) == 0.30


def test_scoring_negative():
    assert villanibench_category_score(0.5, 0.25) == -0.5


def test_scoring_control_zero_one_edges():
    assert villanibench_category_score(0.0, 0.2) == 0.2
    assert villanibench_category_score(1.0, 1.0) == 0.0


def test_category_first_and_missing_control_warning():
    rows = [
        {"runner": "villani", "model": "m", "suite_id": "s", "comparison_mode": "strict", "category": "minimal_patch", "status": "success", "task_id": "1"},
    ]
    scores, warnings = aggregate_model_category_scores(rows)
    assert scores[0]["model_villanibench_score"] is None
    assert warnings
