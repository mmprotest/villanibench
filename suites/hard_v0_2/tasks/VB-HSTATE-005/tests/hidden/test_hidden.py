import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_005.csv_export import actor_ids as csv_metric
from vb_hstate_005.pdf_export import actor_ids as pdf_metric
from vb_hstate_005.email_preview import actor_ids as email_metric
from vb_hstate_005.shared import is_counted


def test_shared_definition_counts_only_explicit_user_actors():
    assert is_counted({'actor_type': 'user'}) is True
    assert is_counted({'actor_type': 'system'}) is False
    assert is_counted({'actor_type': 'service'}) is False
    assert is_counted({'actor_type': 'other'}) is False
    assert is_counted({}) is False


def test_all_paths_use_same_strict_definition():
    records = [
        {'actor_type': 'user'},
        {'actor_type': 'system'},
        {'actor_type': 'service'},
        {'actor_type': 'user'},
        {'actor_type': 'other'},
        {},
    ]
    assert csv_metric(records) == 2
    assert pdf_metric(records) == 2
    assert email_metric(records) == 2
