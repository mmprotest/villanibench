from cache.keys import normalize_key


def invalidate(cache, key: str) -> None:
    cache.delete(normalize_key(key))
