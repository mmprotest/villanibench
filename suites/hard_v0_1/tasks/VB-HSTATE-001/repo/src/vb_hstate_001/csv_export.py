def active_users(records):
    # BUG: stale duplicate definition counts everything except explicit 'suspended'.
    return sum(1 for r in records if r.get('status') != 'suspended')
