def subscription_status(record: dict) -> str:
    # BUG: cancelled subscriptions should not be treated as active just because paid_until is in the future.
    if record.get("paid_until", 0) > record.get("now", 0):
        return "active"
    if record.get("cancelled"):
        return "cancelled"
    return "expired"
