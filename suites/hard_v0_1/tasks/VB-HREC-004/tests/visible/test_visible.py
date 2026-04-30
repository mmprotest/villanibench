import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from webhooks.store import Store


def test_equivalent_key_matches_after_normalisation():
    store = Store()
    store.add('evt-9')
    assert store.contains(' EVT-9 ') is True
