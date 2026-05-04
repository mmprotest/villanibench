import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from demo_sorting.defaults import export_first


def test_export_helper_uses_default_descending_order():
    assert export_first([3, 1, 2]) == 3
