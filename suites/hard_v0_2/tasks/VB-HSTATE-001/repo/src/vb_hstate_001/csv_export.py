def active_users(records):
    return sum(1 for r in records if r.get("status"))
