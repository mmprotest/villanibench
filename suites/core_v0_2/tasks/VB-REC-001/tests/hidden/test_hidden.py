import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from cache.keys import normalize_key

def test_key_normalization_matches_storage_contract():
    assert normalize_key(" Order:ABC ") == "order:abc"
