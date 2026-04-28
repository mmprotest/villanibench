from features.resolver import resolve_flag

def get_feature_enabled(remote_value, fallback: bool) -> bool:
    return resolve_flag(remote_value, fallback)
