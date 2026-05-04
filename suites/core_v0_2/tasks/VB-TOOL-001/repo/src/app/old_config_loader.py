def load_config(env):
    return {"database_url": env.get("DATABASE_URL") or env.get("DB_URL")}
