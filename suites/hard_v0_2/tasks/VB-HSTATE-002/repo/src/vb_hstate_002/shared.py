def is_counted(record: dict) -> bool:
    # BUG: paused subscriptions are not billable, but this still counts them.
    return record.get('state') in {'active', 'paused'}
