import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from mail_preview.preview import preview_total

def test_email_preview_uses_same_net_revenue_source():
    orders = [{"gross": 80.0, "discount": 5.0, "refund": 15.0}]
    assert preview_total(orders) == 60.0
