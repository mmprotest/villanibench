from .normalizer import normalize_id


class Store:
    def __init__(self):
        self._values = set()

    def add(self, key):
        self._values.add(normalize_id(key))

    def contains(self, key):
        return normalize_id(key) in self._values
