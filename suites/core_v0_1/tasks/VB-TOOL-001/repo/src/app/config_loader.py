def load_config(env: dict) -> dict:
    # BUG: migration renamed DB_URL to DATABASE_URL but deployments still set the old key.
    return {"database_url": env.get("DATABASE_URL")}
