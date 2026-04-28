import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from features.client import resolve_many

def test_missing_remote_uses_fallback_in_bulk_path():
    assert resolve_many({"new_nav": None}, {"new_nav": True}) == {"new_nav": True}
