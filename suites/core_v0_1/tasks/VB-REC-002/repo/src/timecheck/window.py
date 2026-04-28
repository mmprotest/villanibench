from timecheck.clock import today


def is_due(record: dict, clock=None) -> bool:
    return record["due_date"] <= today(clock)
