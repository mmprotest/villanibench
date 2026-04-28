from app.config_loader import load_config


def start(env: dict) -> dict:
    cfg = load_config(env)
    if cfg["database_url"] is None:
        raise RuntimeError("database_url is required")
    return cfg
