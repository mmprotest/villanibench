from subscriptions.status import subscription_status

def serialize_subscription(record):
    return {"status": subscription_status(record)}
