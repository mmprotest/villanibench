from .shared import is_counted

def billable_subscriptions(records):
    return sum(1 for r in records if is_counted(r))