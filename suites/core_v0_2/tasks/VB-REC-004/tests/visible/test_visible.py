import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from router.match import match_route

def test_exact_health_route_wins_over_parameter_route():
    assert match_route("/users/health") == "user_health"
