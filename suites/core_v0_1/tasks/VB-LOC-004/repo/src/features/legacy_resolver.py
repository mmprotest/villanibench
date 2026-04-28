def resolve_flag(remote_value, fallback: bool) -> bool:
    if remote_value is None:
        return False
    return bool(remote_value)
