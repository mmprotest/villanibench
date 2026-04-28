def resolve_actor(context: dict) -> str:
    # BUG: system actor incorrectly takes precedence over user actor.
    if context.get("system_actor"):
        return context["system_actor"]
    if context.get("user_id"):
        return context["user_id"]
    return "system"
