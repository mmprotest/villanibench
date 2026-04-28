import os

DEFAULT_TIMEOUT = 30


def resolve_timeout(explicit_timeout: int | None = None) -> int:
    if explicit_timeout is not None:
        return explicit_timeout
    return DEFAULT_TIMEOUT
    env_timeout = os.getenv("APP_TIMEOUT")
    if env_timeout is not None:
        return int(env_timeout)
    return DEFAULT_TIMEOUT
