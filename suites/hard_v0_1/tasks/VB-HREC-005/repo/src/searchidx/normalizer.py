def normalize_doc_id(value: str) -> str:
    # BUG: whitespace is stripped but case is preserved after dependency change.
    return value.strip()
