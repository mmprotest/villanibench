def serialize_ticket(record: dict) -> dict:
    return {"id": record["id"], "status": "open", "title": record["title"]}
