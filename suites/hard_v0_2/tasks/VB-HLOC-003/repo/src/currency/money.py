def convert_cents(cents, rate):
    # BUG: source-of-truth implementation is stale.
    return round(cents) * rate
