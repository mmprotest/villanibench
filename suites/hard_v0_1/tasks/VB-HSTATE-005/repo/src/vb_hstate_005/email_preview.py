from .shared import is_counted


def actor_ids(records):
    return sum(1 for r in records if is_counted(r))
