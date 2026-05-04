from .shared import is_counted


def effective_permissions(records):
    return sum(1 for r in records if is_counted(r))
