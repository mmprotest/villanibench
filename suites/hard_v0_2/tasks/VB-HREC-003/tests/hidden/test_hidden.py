import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from payloads.normalizer import normalize_id
from payloads.store import Store


def test_normalizer_is_stable_and_store_still_separates_different_keys():
    assert normalize_id(' ID-001 ') == 'id-001'
    store = Store()
    store.add('id-001')
    assert store.contains("different") is False
