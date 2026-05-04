def load_config(env: dict) -> dict:
    return {"database_url": env.get("DATABASE_URL")}
