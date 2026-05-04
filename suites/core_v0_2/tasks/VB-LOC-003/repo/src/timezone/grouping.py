def local_day_key(timestamp_hour: int, account_offset_hours: int) -> str:
    # timestamp_hour is hours since day 0 midnight UTC.
    # BUG: ignores the account offset and groups by UTC day.
    day = timestamp_hour // 24
    return f"day-{day}"
