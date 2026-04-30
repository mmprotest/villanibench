from .normalizer import normalize_route


class Store:
    def __init__(self):
        self._values = set()

    def add(self, key):
        self._values.add(normalize_route(key))

    def contains(self, key):
        return normalize_route(key) in self._values
