def normalize_key(key: str) -> str:
    # BUG: dependency upgrade started sending keys with spaces and uppercase.
    return key
