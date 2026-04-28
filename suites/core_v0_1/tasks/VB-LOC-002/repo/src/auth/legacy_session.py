def is_session_valid(session: dict, now: int) -> bool:
    return now < session.get("expires_at", 0)
