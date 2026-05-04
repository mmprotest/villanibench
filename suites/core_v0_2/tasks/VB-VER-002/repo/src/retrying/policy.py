def run_with_retries(operation, max_retries: int):
    attempts = 0
    last_error = None
    # BUG: max_retries means retries after the initial attempt, so this should allow max_retries + 1 attempts.
    while attempts < max_retries:
        attempts += 1
        try:
            return operation()
        except Exception as exc:  # pragma: no cover - tests cover behaviour
            last_error = exc
    raise last_error  # type: ignore[misc]
