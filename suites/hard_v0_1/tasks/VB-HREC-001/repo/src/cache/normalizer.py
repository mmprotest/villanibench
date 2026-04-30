def normalize_key(value: str) -> str:
    # BUG: whitespace is stripped but case is preserved after dependency change.
    return value.strip()
