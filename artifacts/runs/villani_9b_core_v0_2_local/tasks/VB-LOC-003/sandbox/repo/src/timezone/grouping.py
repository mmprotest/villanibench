def local_day_key(timestamp_hour: int, account_offset_hours: int) -> str:
    """Determine which calendar day an event belongs to in the account's timezone.
    
    The timestamp represents hours since midnight of a reference day (day 0) at UTC.
    We need to convert this to the account's local timezone and return the correct
    calendar day key, handling timezone boundaries properly.
    
    Args:
        timestamp_hour: Hours from day-0 midnight in UTC (non-negative integer).
        account_offset_hours: Timezone offset from UTC in hours (e.g., -5 for EST).
        
    Returns:
        Day key string like "day-N" where N is the calendar day index in local timezone.
    """
    # Get the UTC day index and position within that day
    utc_day_index = timestamp_hour // 24
    hour_of_utc_day = timestamp_hour % 24
    
    # Calculate local time's position relative to midnight
    # If adding offset makes us cross into next/prev calendar day, adjust accordingly
    local_offset_from_midnight = hour_of_utc_day + account_offset_hours
    
    if local_offset_from_midnight >= 24:
        # We've crossed into the next day in local timezone
        return f"day-{utc_day_index + 1}"
    elif local_offset_from_midnight < 0:
        # We've crossed back to the previous day in local timezone  
        # Always subtract 1 since hour_of_utc_day + offset < 0 means we're before UTC midnight
        return f"day-{utc_day_index - 1}"
    else:
        # Still within the same calendar day
        return f"day-{utc_day_index}"
