def local_day_key(timestamp_hour: int, account_offset_hours: int) -> str:
    # Convert UTC timestamp to account's local timezone by applying the offset
    day = (timestamp_hour + account_offset_hours) // 24
    return f"day-{day}"
