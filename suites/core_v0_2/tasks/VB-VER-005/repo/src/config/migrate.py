def migrate_config(config: dict) -> dict:
    migrated = dict(config)
    if "timeout_seconds" not in migrated and "timeout" in migrated:
        migrated["timeout_seconds"] = migrated.pop("timeout")
    # BUG: fresh configs should receive the documented default.
    return migrated
