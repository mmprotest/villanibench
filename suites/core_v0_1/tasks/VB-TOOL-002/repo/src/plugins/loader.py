import importlib
from plugins.registry import REGISTRY


def load_plugin(name: str):
    target = REGISTRY[name]
    module_name, func_name = target.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, func_name)
