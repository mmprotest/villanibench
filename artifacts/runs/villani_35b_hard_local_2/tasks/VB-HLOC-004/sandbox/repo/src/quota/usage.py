
def used_units(resources):
    return sum(r["units"] for r in resources if not r.get("archived", False))
