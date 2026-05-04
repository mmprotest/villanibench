import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from feed.pagination import page_after


def test_cursor_between_items_returns_next_larger_items():
    items = [{"id": i} for i in [10, 20, 30, 40]]
    assert page_after(items, cursor=25, limit=2) == [{"id": 30}, {"id": 40}]
