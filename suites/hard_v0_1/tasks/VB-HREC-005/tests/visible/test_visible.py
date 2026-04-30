import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from searchidx.store import Store


def test_equivalent_key_matches_after_normalisation():
    store = Store()
    store.add('doc-77')
    assert store.contains(' Doc-77 ') is True
