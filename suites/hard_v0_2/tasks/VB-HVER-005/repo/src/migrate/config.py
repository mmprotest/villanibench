DEFAULTS = {"send_email": True, "retry_count": 3}


def migrate_config(raw: dict) -> dict:
    migrated = {}
    for key, default in DEFAULTS.items():
        # BUG: falsey explicit values are treated as missing.
        migrated[key] = raw.get(key) or default
    return migrated
