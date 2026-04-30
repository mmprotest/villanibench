def billable_subscriptions(records):
    # BUG: stale duplicate definition counts truthy state values.
    return sum(1 for r in records if r.get('state'))
