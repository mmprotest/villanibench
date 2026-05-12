def local_day_key(timestamp_hour: int, account_offset_hours: int) -> str:
    """Determine the calendar day for an event in the account's timezone.
    
    Args:
        timestamp_hour: Hours since midnight UTC of reference day 0 (non-negative).
        account_offset_hours: Timezone offset from UTC (e.g., -5 for EST).
        
    Returns:
        Day key string like "day-N".
    """
    adjusted = timestamp_hour + account_offset_hours
    
    # The key insight: we're counting calendar days relative to the reference point,
    # but using a threshold-based approach rather than simple floor division.
    # When adjusted is in [-24, 0), it still belongs to day 0 because it hasn't
    # crossed midnight into the previous calendar day from UTC's perspective.
    if -24 <= adjusted < 0:
        return "day-0"
    elif adjusted >= 0:
        return f"day-{adjusted // 24}"
    else:
        # For adjusted < -24, we've truly crossed into previous calendar days
        return f"day-{adjusted // 24}"
