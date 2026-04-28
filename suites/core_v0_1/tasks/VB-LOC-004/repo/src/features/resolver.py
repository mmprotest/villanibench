def resolve_flag(remote_value, fallback: bool) -> bool:
    if remote_value is None:
        return False
    return bool(remote_value)


def resolve_feature_map(remote_flags: dict[str, object], fallback_flags: dict[str, bool]) -> dict[str, bool]:
    resolved: dict[str, bool] = {}
    for key, fallback in fallback_flags.items():
        resolved[key] = resolve_flag(remote_flags.get(key), fallback)
    return resolved
