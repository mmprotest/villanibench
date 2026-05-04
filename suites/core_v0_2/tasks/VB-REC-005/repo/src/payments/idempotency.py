def make_idempotency_key(request: dict, attempt: int) -> str:
    # BUG: idempotency key changes per retry attempt.
    return f"{request['customer']}:{request['amount']}:{attempt}"
