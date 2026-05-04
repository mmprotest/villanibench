from datetime import date


def today(clock=None):
    # BUG: ignores injected clock, making tests and jobs use real date.
    return date.today()
