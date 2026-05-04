from .plugins.json_plugin import handle as json_handler
from .plugins.bank_transfer_plugin import handle as bank_transfer_handler

REGISTRY = {
    "json": json_handler,
    # BUG: bank_transfer plugin exists but is not registered.
}


def resolve(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown payment: {name}")
    return REGISTRY[name]
