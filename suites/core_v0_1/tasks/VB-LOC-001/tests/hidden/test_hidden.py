import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from invoice.export import export_invoice_total

def test_zero_discount_is_stable():
    assert export_invoice_total(80.0, 0.0, 0.15) == 92.0
