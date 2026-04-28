def resolve_permission(chain: list[dict]) -> bool:
    # chain is ordered from parent to child. Child explicit values should win.
    allowed = False
    for level in chain:
        if level.get("allow") is True:
            allowed = True
        # BUG: explicit deny is ignored once a parent allowed.
    return allowed
