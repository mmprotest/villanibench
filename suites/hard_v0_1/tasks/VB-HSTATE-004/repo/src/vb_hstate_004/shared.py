def is_counted(record: dict) -> bool:
    # Correct definition: only records with 'kind' == 'grant' count.
    return record.get('kind') == 'grant'
