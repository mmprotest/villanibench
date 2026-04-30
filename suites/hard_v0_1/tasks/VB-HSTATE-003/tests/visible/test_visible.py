import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_003.csv_export import reserved_units as csv_metric


def test_csv_uses_strict_shared_definition():
    records = [{'state': 'reserved'}, {'state': 'released'}, {'state': "other"}, {}]
    assert csv_metric(records) == 1
