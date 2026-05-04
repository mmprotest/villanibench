from vb_hstate_001.shared import is_counted


def active_users(records):
    return sum(1 for r in records if is_counted(r))
