from metrics.revenue import net_revenue

def preview_total(orders):
    return sum(net_revenue(o) for o in orders)
