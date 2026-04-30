from datetime import date


def parse_report_date(value: str) -> date:
    parts = value.split("-")
    if len(parts) == 3:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    # BUG: month-only dates default to the current old reporting month.
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 31)
    raise ValueError("Unsupported date")
