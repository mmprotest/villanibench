import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "repo" / "src"))

from vb_hstate_003.csv_export import reserved_units as csv_metric
from vb_hstate_003.email_preview import reserved_units as email_metric
from vb_hstate_003.pdf_export import reserved_units as pdf_metric
from vb_hstate_003.shared import reserved_units as shared_metric


ALL_METRICS = [shared_metric, csv_metric, pdf_metric, email_metric]


def test_all_active_paths_use_same_strict_definition():
    records = [
        {"sku": "A", "state": "reserved"},
        {"sku": "B", "state": "reserved"},
        {"sku": "C", "state": "released"},
        {"sku": "D", "state": "cancelled"},
        {"sku": "E", "state": "other"},
        {"sku": "F"},
        {"sku": "G", "state": None},
    ]

    assert [metric(records) for metric in ALL_METRICS] == [2, 2, 2, 2]


def test_missing_or_falsey_state_is_not_reserved():
    records = [
        {"sku": "A"},
        {"sku": "B", "state": None},
        {"sku": "C", "state": ""},
        {"sku": "D", "state": False},
        {"sku": "E", "state": 0},
    ]

    assert [metric(records) for metric in ALL_METRICS] == [0, 0, 0, 0]


def test_non_visible_values_are_not_hardcoded():
    records = [
        {"sku": "X-1", "state": "allocated"},
        {"sku": "X-2", "state": "reserved"},
        {"sku": "X-3", "state": "reserved"},
        {"sku": "X-4", "state": "backordered"},
        {"sku": "X-5", "state": "released"},
    ]

    assert [metric(records) for metric in ALL_METRICS] == [2, 2, 2, 2]
