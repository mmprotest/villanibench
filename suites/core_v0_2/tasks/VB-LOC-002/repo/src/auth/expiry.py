def is_session_valid(session: dict, now: int) -> bool:
    expiry = session.get("original_expires_at", session.get("expires_at", 0))
    return now < expiry
