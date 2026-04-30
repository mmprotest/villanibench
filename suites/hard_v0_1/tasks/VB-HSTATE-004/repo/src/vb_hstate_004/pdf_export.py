def effective_permissions(records):
    # BUG: stale duplicate definition counts missing states.
    return sum(1 for r in records if r.get('kind') in ('grant', None))
