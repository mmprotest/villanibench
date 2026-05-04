import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repo" / "src"))

from auth.session import refresh_session, can_access


def test_refreshed_session_boundary_uses_new_expiry():
    session = {"user_id": "u2", "original_expires_at": 50, "expires_at": 50}
    refreshed = refresh_session(session, now=50, extension_seconds=10)
    assert can_access(refreshed, now=59) is True
    assert can_access(refreshed, now=60) is False


def test_legacy_original_expiry_still_works_when_expires_at_missing():
    session = {"user_id": "legacy", "original_expires_at": 30}
    assert can_access(session, now=29) is True
    assert can_access(session, now=30) is False
