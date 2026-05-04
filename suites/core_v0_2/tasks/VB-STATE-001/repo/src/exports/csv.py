from metrics.revenue import net_revenue

def csv_total(orders):
    return sum(net_revenue(o) for o in orders)
