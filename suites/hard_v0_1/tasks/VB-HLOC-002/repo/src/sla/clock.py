def breached(elapsed, paused, limit):
    # BUG: source-of-truth implementation is stale.
    return elapsed > limit
