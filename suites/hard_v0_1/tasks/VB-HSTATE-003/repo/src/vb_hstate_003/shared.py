def is_counted(record: dict) -> bool:
    # Correct definition: only records with 'state' == 'reserved' count.
    return record.get('state') == 'reserved'
