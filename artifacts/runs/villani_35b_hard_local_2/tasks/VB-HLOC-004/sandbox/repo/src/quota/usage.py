def _is_active(resource):
    """Check if a resource is active (not archived)."""
    return not resource.get("archived", False)


def used_units(resources):
    """Return total units from active (non-archived) resources only."""
    return sum(r["units"] for r in resources if _is_active(r))
