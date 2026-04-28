def validate_order(order: dict) -> bool:
    return isinstance(order.get("id"), str) and order["id"].startswith("ord_") and order.get("amount", 0) > 0
