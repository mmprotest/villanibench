from .plugins.json_plugin import handle as json_handler
from .plugins.yaml_plugin import handle as yaml_handler

REGISTRY = {
    "json": json_handler,
    # BUG: yaml plugin exists but is not registered.
}


def resolve(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown exporter: {name}")
    return REGISTRY[name]
