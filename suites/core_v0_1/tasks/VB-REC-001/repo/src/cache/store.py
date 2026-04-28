class Cache:
    def __init__(self):
        self.values = {}
    def set(self, key, value):
        self.values[key] = value
    def delete(self, key):
        self.values.pop(key, None)
    def get(self, key):
        return self.values.get(key)
