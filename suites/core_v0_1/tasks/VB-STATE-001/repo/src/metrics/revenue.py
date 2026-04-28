def net_revenue(order: dict) -> float:
    # BUG: refunds must reduce net revenue everywhere.
    return float(order["gross"] - order.get("discount", 0.0))
