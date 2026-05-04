import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_004.pdf_export import effective_permissions as pdf_metric
from vb_hstate_004.email_preview import effective_permissions as email_metric


def test_pdf_and_email_use_same_strict_definition():
    records = [{'kind': 'grant'}, {'kind': 'deny'}, {'kind': "other"}, {}]
    assert pdf_metric(records) == 1
    assert email_metric(records) == 1
