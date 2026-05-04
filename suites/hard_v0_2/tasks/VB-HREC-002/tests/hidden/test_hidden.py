import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from authz.normalizer import normalize_route
from authz.store import Store


def test_normalizer_is_stable_and_store_still_separates_different_keys():
    assert normalize_route('/Admin/Users/') == '/admin/users'
    store = Store()
    store.add('/admin/users')
    assert store.contains("different") is False
