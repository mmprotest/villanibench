def local_day_key(timestamp_hour: int, account_offset_hours: int) -> str:
    return f"day-{(timestamp_hour + account_offset_hours) // 24}"
