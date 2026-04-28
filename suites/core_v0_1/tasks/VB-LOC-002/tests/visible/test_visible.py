import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from auth.session import refresh_session, can_access

def test_refreshed_session_uses_new_expiry():
    session = {"user_id": "u1", "original_expires_at": 100, "expires_at": 100}
    refreshed = refresh_session(session, now=100, extension_seconds=60)
    assert can_access(refreshed, now=120) is True
