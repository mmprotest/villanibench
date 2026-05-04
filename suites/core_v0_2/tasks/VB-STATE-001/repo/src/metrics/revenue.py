def net_revenue(order: dict) -> float:
    return float(order["gross"] - order.get("discount", 0.0))
