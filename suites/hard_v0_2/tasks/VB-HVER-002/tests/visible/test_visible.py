import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from feed.pagination import page_after


def test_cursor_excludes_previous_last_item():
    items = [{"id": i} for i in [1, 2, 3, 4]]
    assert page_after(items, cursor=2, limit=2) == [{"id": 3}, {"id": 4}]
