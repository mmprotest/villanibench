def page_after(items, cursor, limit):
    # Items are sorted ascending by integer id.
    start = 0
    if cursor is not None:
        for i, item in enumerate(items):
            if item["id"] >= cursor:  # BUG: includes cursor item again.
                start = i
                break
    return items[start:start + limit]
