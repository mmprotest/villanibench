from .plugins.json_plugin import handle as json_handler
from .plugins.slug_plugin import handle as slug_handler

REGISTRY = {
    "json": json_handler,
    # BUG: slug plugin exists but is not registered.
}


def resolve(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown transform: {name}")
    return REGISTRY[name]
