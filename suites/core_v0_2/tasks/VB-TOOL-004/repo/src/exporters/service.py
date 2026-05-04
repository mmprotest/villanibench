from exporters.registry import EXPORTERS


def export(rows, format_name: str) -> str:
    return EXPORTERS[format_name](rows)
