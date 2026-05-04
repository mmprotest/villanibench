from payments.idempotency import make_idempotency_key


def build_attempts(request: dict, max_retries: int) -> list[str]:
    return [make_idempotency_key(request, attempt) for attempt in range(max_retries + 1)]
