def billable_subscriptions(records):
    # BUG: stale duplicate definition counts everything except explicit 'paused'.
    return sum(1 for r in records if r.get('state') != 'paused')
