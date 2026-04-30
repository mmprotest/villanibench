def is_counted(record: dict) -> bool:
    # Correct definition: only records with 'state' == 'active' count.
    return record.get('state') == 'active'
