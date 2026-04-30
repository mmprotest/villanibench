import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_001.pdf_export import active_users as pdf_metric
from vb_hstate_001.email_preview import active_users as email_metric


def test_pdf_and_email_use_same_strict_definition():
    records = [{'status': 'active'}, {'status': 'suspended'}, {'status': "other"}, {}]
    assert pdf_metric(records) == 1
    assert email_metric(records) == 1
