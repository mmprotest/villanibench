from .normalizer import normalize_doc_id


class Store:
    def __init__(self):
        self._values = set()

    def add(self, key):
        self._values.add(normalize_doc_id(key))

    def contains(self, key):
        return normalize_doc_id(key) in self._values
