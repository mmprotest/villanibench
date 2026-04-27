from villanibench.harness.budget import get_budget_profile


def test_budget_profile_loading():
    b = get_budget_profile("lite_v0_1")
    assert b.wall_time_sec == 120
