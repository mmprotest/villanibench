import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from invoice.export import export_invoice_total

def test_discount_amount_applied_before_tax():
    assert export_invoice_total(200.0, 25.0, 0.10) == 192.5
