import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from factory.orders import make_order
from orders.validation import validate_order

def test_factory_custom_id_still_respected():
    assert validate_order(make_order(order_id="ord_custom")) is True
