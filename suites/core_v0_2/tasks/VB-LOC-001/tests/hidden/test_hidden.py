import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from invoice.export import export_invoice_total


def test_discount_amount_with_different_tax_rate():
    assert export_invoice_total(200.0, 25.0, 0.10) == 192.5


def test_discount_amount_with_fractional_values_rounds_final_total():
    assert export_invoice_total(49.99, 5.55, 0.075) == 47.77
