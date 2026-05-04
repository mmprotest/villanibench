from audit.actor import resolve_actor

def manual_sync_event(context):
    return {"actor": resolve_actor(context)}
