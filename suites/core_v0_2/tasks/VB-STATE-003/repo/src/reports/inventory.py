from inventory.delta import reservation_delta

def report_reserved(events):
    return sum(reservation_delta(e) for e in events)
