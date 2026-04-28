def resolve_feature_value(remote_value: bool | None, fallback: bool) -> bool:
    return fallback if remote_value is None else bool(remote_value)
