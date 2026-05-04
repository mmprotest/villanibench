import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from paging.cursor import page_items

def test_cursor_for_larger_list_advances_exactly_by_limit():
    first, cursor = page_items(["a", "b", "c", "d", "e"], None, 3)
    second, _ = page_items(["a", "b", "c", "d", "e"], cursor, 3)
    assert first == ["a", "b", "c"]
    assert second == ["d", "e"]
