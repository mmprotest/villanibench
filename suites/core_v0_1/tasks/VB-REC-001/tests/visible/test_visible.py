import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from cache.store import Cache
from cache.invalidation import invalidate

def test_invalidation_normalizes_key_case():
    cache = Cache()
    cache.set("user:42", "cached")
    invalidate(cache, " USER:42 ")
    assert cache.get("user:42") is None
