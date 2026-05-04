import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from webhooks.normalizer import normalize_event_id
from webhooks.store import Store


def test_normalizer_is_stable_and_store_still_separates_different_keys():
    assert normalize_event_id(' EVT-9 ') == 'evt-9'
    store = Store()
    store.add('evt-9')
    assert store.contains("different") is False
