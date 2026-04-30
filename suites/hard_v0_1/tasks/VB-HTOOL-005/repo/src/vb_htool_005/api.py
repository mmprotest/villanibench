from .registry import resolve


def run(name, value):
    return resolve(name)(value)
