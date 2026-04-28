import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from features.resolver import resolve_feature_map

def test_feature_map_missing_remote_uses_fallback_for_each_key():
    resolved = resolve_feature_map({"search_v2": False}, {"search_v2": True, "beta_banner": True})
    assert resolved["search_v2"] is False
    assert resolved["beta_banner"] is True
