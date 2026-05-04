import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

import router.match as match_module
from router.match import match_route


def test_exact_health_route_still_wins_after_other_user_ids():
    assert match_route("/users/health") == "user_health"


def test_parameter_route_still_matches_regular_user_id():
    assert match_route("/users/123") == "user_detail"


def test_exact_precedence_is_generic_not_hardcoded(monkeypatch):
    monkeypatch.setattr(
        match_module,
        "ROUTES",
        [
            ("/projects/<id>", "project_detail"),
            ("/projects/health", "project_health"),
        ],
    )

    assert match_module.match_route("/projects/health") == "project_health"
    assert match_module.match_route("/projects/abc") == "project_detail"
