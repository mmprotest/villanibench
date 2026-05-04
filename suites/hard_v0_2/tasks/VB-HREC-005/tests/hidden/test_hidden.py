import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from searchidx.normalizer import normalize_doc_id
from searchidx.store import Store


def test_normalizer_is_stable_and_store_still_separates_different_keys():
    assert normalize_doc_id(' Doc-77 ') == 'doc-77'
    store = Store()
    store.add('doc-77')
    assert store.contains("different") is False
