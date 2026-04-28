def serialize_ticket(record: dict) -> dict:
    # BUG: status is overwritten during serialization.
    return {"id": record["id"], "status": "open", "title": record["title"]}
