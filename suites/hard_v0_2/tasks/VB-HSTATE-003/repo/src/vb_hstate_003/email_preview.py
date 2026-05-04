def reserved_units(records):
    # BUG: stale duplicate definition counts every truthy state.
    return sum(1 for r in records if r.get("state"))
