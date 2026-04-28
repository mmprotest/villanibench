from timezone.grouping import local_day

def group_day(timestamp_utc: int, account_tz_offset_hours: int) -> int:
    return local_day(timestamp_utc, account_tz_offset_hours)
