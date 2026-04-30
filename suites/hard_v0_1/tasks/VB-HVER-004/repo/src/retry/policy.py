TRANSIENT = {"timeout", "rate_limit", "connection_reset"}
PERMANENT = {"validation", "permission", "not_found"}


def should_retry(error_code: str, attempt: int, max_attempts: int = 3) -> bool:
    if attempt >= max_attempts:
        return False
    # BUG: dependency now prefixes transient errors with provider names.
    return error_code in TRANSIENT or error_code not in PERMANENT
