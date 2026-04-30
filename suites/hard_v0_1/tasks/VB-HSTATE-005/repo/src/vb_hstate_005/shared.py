def is_counted(record: dict) -> bool:
    # Correct definition: only records with 'actor_type' == 'user' count.
    return record.get('actor_type') == 'user'
