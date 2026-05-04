import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from vb_hstate_003.csv_export import reserved_units as csv_metric


def test_csv_uses_strict_reserved_definition():
    records = [
        {"sku": "A", "state": "reserved", "units": 2},
        {"sku": "B", "state": "released", "units": 5},
        {"sku": "C", "state": "cancelled", "units": 3},
        {"sku": "D", "state": "other", "units": 7},
        {"sku": "E"},
        {"sku": "F", "state": ""},
    ]

    assert csv_metric(records) == 1
