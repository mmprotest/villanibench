import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from payments.idempotency import make_idempotency_key

def test_key_does_not_include_attempt_number():
    request = {"customer": "c2", "amount": 75}
    assert make_idempotency_key(request, 0) == make_idempotency_key(request, 3) == "c2:75"
