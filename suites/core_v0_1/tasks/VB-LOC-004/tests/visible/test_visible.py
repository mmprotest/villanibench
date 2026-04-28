import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from features.client import get_feature_enabled

def test_missing_remote_uses_fallback_true():
    assert get_feature_enabled(None, True) is True
