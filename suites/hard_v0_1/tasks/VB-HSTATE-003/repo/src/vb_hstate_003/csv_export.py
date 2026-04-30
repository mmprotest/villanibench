def reserved_units(records):
    # BUG: stale duplicate definition counts everything except explicit 'released'.
    return sum(1 for r in records if r.get('state') != 'released')
