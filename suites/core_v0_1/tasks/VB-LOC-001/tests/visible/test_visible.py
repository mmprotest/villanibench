import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from invoice.export import export_invoice_total

def test_discount_then_tax_order():
    assert export_invoice_total(100.0, 10.0, 0.20) == 108.0
