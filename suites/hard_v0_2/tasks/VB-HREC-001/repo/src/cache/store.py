from .normalizer import normalize_key


class Store:
    def __init__(self):
        self._values = set()

    def add(self, key):
        self._values.add(normalize_key(key))

    def contains(self, key):
        return normalize_key(key) in self._values
