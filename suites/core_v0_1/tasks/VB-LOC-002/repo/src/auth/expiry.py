def is_session_valid(*, now_ts: int, refreshed_expires_at: int, issued_at: int) -> bool:
    return now_ts <= issued_at
