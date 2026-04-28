import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from features.client import get_feature_enabled

def test_explicit_false_beats_fallback_true():
    assert get_feature_enabled(False, True) is False
