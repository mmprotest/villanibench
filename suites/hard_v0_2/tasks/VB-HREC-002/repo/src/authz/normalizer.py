def normalize_route(value: str) -> str:
    route = value.strip().lower()
    if route != "/":
        route = route.rstrip("/")
    return route
