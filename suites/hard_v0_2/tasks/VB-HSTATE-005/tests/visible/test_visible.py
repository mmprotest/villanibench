import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_005.csv_export import actor_ids as csv_metric


def test_csv_uses_strict_shared_definition():
    records = [{'actor_type': 'user'}, {'actor_type': 'system'}, {'actor_type': 'other'}, {}]
    assert csv_metric(records) == 1


def test_csv_counts_multiple_real_users_only():
    records = [
        {'actor_type': 'user'},
        {'actor_type': 'service'},
        {'actor_type': 'user'},
        {'actor_type': None},
    ]
    assert csv_metric(records) == 2
