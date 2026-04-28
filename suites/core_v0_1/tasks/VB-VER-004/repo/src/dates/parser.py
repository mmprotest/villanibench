from datetime import date


def parse_report_date(value: str) -> date:
    # BUG: docs allow YYYY/MM/DD too, but only dash format is accepted.
    parts = value.split("-")
    if len(parts) != 3:
        raise ValueError("date must be YYYY-MM-DD or YYYY/MM/DD")
    year, month, day = [int(p) for p in parts]
    return date(year, month, day)
