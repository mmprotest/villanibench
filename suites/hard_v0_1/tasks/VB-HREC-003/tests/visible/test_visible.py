import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from payloads.store import Store


def test_equivalent_key_matches_after_normalisation():
    store = Store()
    store.add('id-001')
    assert store.contains(' ID-001 ') is True
