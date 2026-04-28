def make_order(order_id: str | None = None, amount: int = 100) -> dict:
    # BUG: default id is not accepted by validators.
    return {"id": order_id or "order-1", "amount": amount}
