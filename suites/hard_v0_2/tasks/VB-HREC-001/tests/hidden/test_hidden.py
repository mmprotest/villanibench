import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from cache.normalizer import normalize_key
from cache.store import Store


def test_normalizer_strips_whitespace_and_lowercases_keys():
    assert normalize_key(' User:42 ') == 'user:42'
    assert normalize_key('\tADMIN:99\n') == 'admin:99'


def test_store_uses_normalized_keys_for_add_and_lookup():
    store = Store()
    store.add(' User:42 ')
    assert store.contains('user:42') is True
    assert store.contains('USER:42') is True


def test_store_still_separates_different_keys():
    store = Store()
    store.add('user:42')
    assert store.contains('different') is False
