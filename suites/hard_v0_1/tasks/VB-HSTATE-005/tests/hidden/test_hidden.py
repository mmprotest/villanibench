import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_005.pdf_export import actor_ids as pdf_metric
from vb_hstate_005.email_preview import actor_ids as email_metric


def test_pdf_and_email_use_same_strict_definition():
    records = [{'actor_type': 'user'}, {'actor_type': 'system'}, {'actor_type': "other"}, {}]
    assert pdf_metric(records) == 1
    assert email_metric(records) == 1
