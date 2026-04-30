import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_002.pdf_export import billable_subscriptions as pdf_metric
from vb_hstate_002.email_preview import billable_subscriptions as email_metric


def test_pdf_and_email_use_same_strict_definition():
    records = [{'state': 'active'}, {'state': 'paused'}, {'state': "other"}, {}]
    assert pdf_metric(records) == 1
    assert email_metric(records) == 1
