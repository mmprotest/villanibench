import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from payments.retry import build_attempts

def test_retry_uses_same_idempotency_key_for_every_attempt():
    keys = build_attempts({"customer": "c1", "amount": 50}, max_retries=2)
    assert keys == ["c1:50", "c1:50", "c1:50"]
