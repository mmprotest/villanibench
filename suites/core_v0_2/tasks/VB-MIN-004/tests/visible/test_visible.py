import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_sorting.defaults import sort_values


def test_default_sort_order_is_descending():
    assert sort_values([3, 1, 2]) == [3, 2, 1]
