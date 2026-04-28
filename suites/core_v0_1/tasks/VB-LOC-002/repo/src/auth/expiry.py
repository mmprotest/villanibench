def is_session_valid(session: dict, now: int) -> bool:
    # BUG: refreshed sessions carry refreshed_at, but validity still uses the stale original expiry.
    expiry = session.get("original_expires_at", session.get("expires_at", 0))
    return now < expiry
