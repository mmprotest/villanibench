import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from cache.store import Store


def test_equivalent_key_matches_after_normalisation():
    store = Store()
    store.add('user:42')
    assert store.contains(' User:42 ') is True
