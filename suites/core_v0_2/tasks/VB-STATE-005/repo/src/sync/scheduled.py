from audit.actor import resolve_actor

def scheduled_sync_event(context):
    return {"actor": resolve_actor(context)}
