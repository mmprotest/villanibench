def used_units(resources):
    # BUG: source-of-truth implementation is stale.
    return sum(r["units"] for r in resources)
