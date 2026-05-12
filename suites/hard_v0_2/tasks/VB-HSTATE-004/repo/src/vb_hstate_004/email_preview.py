def effective_permissions(records):
    return sum(1 for r in records if r.get("kind") in {"grant", "other"})
