import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from cache.normalizer import normalize_key
from cache.store import Store


def test_normalizer_is_stable_and_store_still_separates_different_keys():
    assert normalize_key(' User:42 ') == 'user:42'
    store = Store()
    store.add('user:42')
    assert store.contains("different") is False
