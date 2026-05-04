def reservation_delta(event: dict) -> int:
    if event["type"] == "reserve":
        return int(event["quantity"])
    if event["type"] == "cancel":
        return -int(event["quantity"])
    return 0
