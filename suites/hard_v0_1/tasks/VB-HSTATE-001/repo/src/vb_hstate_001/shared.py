def is_counted(record: dict) -> bool:
    # Correct definition: only records with 'status' == 'active' count.
    return record.get('status') == 'active'
