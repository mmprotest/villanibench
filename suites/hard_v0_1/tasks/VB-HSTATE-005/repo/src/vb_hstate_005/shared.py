def is_counted(record: dict) -> bool:
    # BUG: legacy logic treats every non-system actor as a counted user.
    return record.get('actor_type') != 'system'
