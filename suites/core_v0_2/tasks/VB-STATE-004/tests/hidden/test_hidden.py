import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from api.access import can_access
from permissions.resolver import resolve_permission
from ui.sidebar import show_project


def test_child_allow_overrides_parent_deny():
    assert resolve_permission([{"allow": False}, {"allow": True}]) is True


def test_nearest_explicit_permission_wins_across_intermediate_levels():
    chain = [{"allow": True}, {"team": "platform"}, {"allow": False}]
    assert resolve_permission(chain) is False


def test_missing_intermediate_level_does_not_clear_later_allow():
    chain = [{"allow": False}, {"team": "platform"}, {"allow": True}]
    assert can_access(chain) is True


def test_all_call_sites_share_fixed_resolver_semantics():
    chain = [{"allow": True}, {"allow": False}, {"allow": True}]
    assert can_access(chain) is True
    assert show_project(chain) is True


def test_hard_coded_visible_chain_is_not_enough():
    chain = [{"allow": True}, {"team": "middle"}, {"allow": False}, {"team": "leaf"}]
    assert resolve_permission(chain) is False
