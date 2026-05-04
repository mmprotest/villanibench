from inventory.delta import reservation_delta

def reserved_total(events):
    return sum(reservation_delta(e) for e in events)
