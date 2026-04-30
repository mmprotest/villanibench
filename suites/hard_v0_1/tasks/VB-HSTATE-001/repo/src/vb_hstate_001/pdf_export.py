def active_users(records):
    # BUG: stale duplicate definition counts missing states.
    return sum(1 for r in records if r.get('status') in ('active', None))
