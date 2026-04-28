from auth.expiry import is_session_valid


def refresh_session(session: dict, now: int, extension_seconds: int) -> dict:
    refreshed = dict(session)
    refreshed["expires_at"] = now + extension_seconds
    return refreshed


def can_access(session: dict, now: int) -> bool:
    return is_session_valid(session, now)
