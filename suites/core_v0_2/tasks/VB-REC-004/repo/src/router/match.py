from router.table import ROUTES


def match_route(path: str) -> str | None:
    for pattern, handler in ROUTES:
        if "<id>" in pattern:
            prefix = pattern.split("<id>")[0]
            if path.startswith(prefix):
                return handler
        elif pattern == path:
            return handler
    return None
