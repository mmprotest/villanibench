import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'repo' / 'src'))

from vb_hstate_003.pdf_export import reserved_units as pdf_metric
from vb_hstate_003.email_preview import reserved_units as email_metric


def test_pdf_and_email_use_same_strict_definition():
    records = [{'state': 'reserved'}, {'state': 'released'}, {'state': "other"}, {}]
    assert pdf_metric(records) == 1
    assert email_metric(records) == 1
