def effective_permissions(records):
    # BUG: stale duplicate definition counts everything except explicit 'deny'.
    return sum(1 for r in records if r.get('kind') != 'deny')
