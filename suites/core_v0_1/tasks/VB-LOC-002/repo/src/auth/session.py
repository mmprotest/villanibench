from auth.expiry import is_session_valid

def is_refreshed_session_valid(*, now_ts: int, refreshed_expires_at: int, issued_at: int) -> bool:
    return is_session_valid(now_ts=now_ts, refreshed_expires_at=refreshed_expires_at, issued_at=issued_at)
