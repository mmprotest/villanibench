DEFAULT_SORT_ORDER = "ascending"


def sort_values(values: list[int], sort_order: str | None = None) -> list[int]:
    order = sort_order or DEFAULT_SORT_ORDER
    return sorted(values, reverse=(order == "descending"))


def export_first(values: list[int], sort_order: str | None = None) -> int:
    return sort_values(values, sort_order)[0]
