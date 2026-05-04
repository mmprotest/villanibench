import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from dashboard.view import dashboard_total
from exports.csv import csv_total

def test_dashboard_and_csv_use_refunds():
    orders = [{"gross": 100.0, "discount": 10.0, "refund": 25.0}]
    assert dashboard_total(orders) == 65.0
    assert csv_total(orders) == 65.0
