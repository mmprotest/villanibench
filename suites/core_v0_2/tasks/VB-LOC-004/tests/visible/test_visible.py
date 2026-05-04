import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from features.client import is_enabled


def test_missing_remote_uses_true_fallback():
    assert is_enabled(None, True) is True


def test_missing_remote_uses_false_fallback():
    assert is_enabled(None, False) is False
