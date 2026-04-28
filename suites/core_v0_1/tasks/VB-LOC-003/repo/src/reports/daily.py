from timezone.grouping import local_day_key


def group_daily_counts(events: list[dict], account_offset_hours: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        key = local_day_key(event["timestamp_hour"], account_offset_hours)
        counts[key] = counts.get(key, 0) + 1
    return counts
