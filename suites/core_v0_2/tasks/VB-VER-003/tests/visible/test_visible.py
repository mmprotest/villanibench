import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from paging.cursor import page_items

def test_second_page_does_not_repeat_last_item():
    first, cursor = page_items(["a", "b", "c", "d"], None, 2)
    second, _ = page_items(["a", "b", "c", "d"], cursor, 2)
    assert first == ["a", "b"]
    assert second == ["c", "d"]
