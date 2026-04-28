SECONDS_PER_DAY = 24 * 60 * 60

def local_day(timestamp_utc: int, account_tz_offset_hours: int) -> int:
    return timestamp_utc // SECONDS_PER_DAY
