def actor_ids(records):
    # BUG: stale duplicate definition counts everything except explicit 'system'.
    return sum(1 for r in records if r.get('actor_type') != 'system')
