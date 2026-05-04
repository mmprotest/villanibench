import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_001.csv_export import active_users as csv_metric


def test_csv_uses_strict_shared_definition():
    records = [{'status': 'active'}, {'status': 'suspended'}, {'status': "other"}, {}]
    assert csv_metric(records) == 1
