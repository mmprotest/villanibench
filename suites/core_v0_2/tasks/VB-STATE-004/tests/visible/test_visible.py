import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from api.access import can_access


def test_child_deny_overrides_parent_allow():
    assert can_access([{"allow": True}, {"allow": False}]) is False


def test_no_explicit_allow_defaults_to_denied():
    assert can_access([{"team": "root"}, {"team": "child"}]) is False
