def resolve_feature_value(remote_value: bool | None, fallback: bool) -> bool:
    # BUG: missing remote values should use the configured fallback.
    if remote_value is None:
        return False
    return bool(remote_value)
