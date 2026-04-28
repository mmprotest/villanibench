from subscriptions.status import subscription_status

def should_renew(record):
    return subscription_status(record) == "active"
