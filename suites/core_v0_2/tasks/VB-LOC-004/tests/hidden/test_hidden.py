import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from features.client import resolve_many
from features.resolver import resolve_feature_value


def test_missing_remote_uses_fallback_in_bulk_path():
    assert resolve_many({"new_nav": None}, {"new_nav": True}) == {"new_nav": True}


def test_remote_value_takes_precedence_over_fallback():
    assert resolve_feature_value(False, True) is False
    assert resolve_feature_value(True, False) is True


def test_bulk_path_preserves_remote_values_and_missing_key_fallbacks():
    assert resolve_many(
        {"new_nav": None, "beta_checkout": False, "fast_search": True},
        {"new_nav": True, "beta_checkout": True, "fast_search": False, "audit_log": False},
    ) == {
        "new_nav": True,
        "beta_checkout": False,
        "fast_search": True,
        "audit_log": False,
    }
