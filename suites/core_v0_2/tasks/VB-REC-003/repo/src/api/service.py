from db.adapter import load_ticket
from api.serializer import serialize_ticket


def get_ticket(ticket_id: str) -> dict:
    return serialize_ticket(load_ticket(ticket_id))
