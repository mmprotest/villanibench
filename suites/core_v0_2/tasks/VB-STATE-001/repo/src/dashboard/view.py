from metrics.revenue import net_revenue

def dashboard_total(orders):
    return sum(net_revenue(o) for o in orders)
