def page_items(items: list[str], cursor: int | None, limit: int) -> tuple[list[str], int | None]:
    start = 0 if cursor is None else cursor
    page = items[start:start + limit]
    if start + limit >= len(items):
        next_cursor = None
    else:
        # BUG: next page starts at the last item already returned.
        next_cursor = start + limit - 1
    return page, next_cursor
