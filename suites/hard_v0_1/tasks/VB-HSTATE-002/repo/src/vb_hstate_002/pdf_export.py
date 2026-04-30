def billable_subscriptions(records):
    # BUG: stale duplicate definition counts missing states.
    return sum(1 for r in records if r.get('state') in ('active', None))
