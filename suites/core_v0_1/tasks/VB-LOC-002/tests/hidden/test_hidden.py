import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'repo' / 'src'))

from auth.session import is_refreshed_session_valid

def test_already_expired_session_is_invalid():
    assert is_refreshed_session_valid(now_ts=201, refreshed_expires_at=200, issued_at=50) is False
