from .plugins.json_plugin import handle as json_handler
from .plugins.sms_plugin import handle as sms_handler

REGISTRY = {
    "json": json_handler,
    "sms": sms_handler,
}


def resolve(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown channel: {name}")
    return REGISTRY[name]
