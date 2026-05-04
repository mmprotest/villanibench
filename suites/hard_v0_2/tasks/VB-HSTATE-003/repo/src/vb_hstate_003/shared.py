def reserved_units(records):
    # BUG: shared definition is too broad and counts every truthy state.
    return sum(1 for r in records if r.get("state"))
