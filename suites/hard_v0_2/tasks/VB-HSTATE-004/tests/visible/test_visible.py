import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_004.csv_export import effective_permissions as csv_metric


def test_csv_uses_strict_shared_definition():
    records = [{'kind': 'grant'}, {'kind': 'deny'}, {'kind': "other"}, {}]
    assert csv_metric(records) == 1
