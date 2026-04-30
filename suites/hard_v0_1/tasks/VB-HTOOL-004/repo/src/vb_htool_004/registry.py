from .plugins.json_plugin import handle as json_handler
from .plugins.markdown_plugin import handle as markdown_handler

REGISTRY = {
    "json": json_handler,
    # BUG: markdown plugin exists but is not registered.
}


def resolve(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown renderer: {name}")
    return REGISTRY[name]
