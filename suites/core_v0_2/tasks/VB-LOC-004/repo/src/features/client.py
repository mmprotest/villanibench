from features.resolver import resolve_feature_value


def is_enabled(remote_value: bool | None, fallback: bool) -> bool:
    return resolve_feature_value(remote_value, fallback)


def resolve_many(values: dict[str, bool | None], fallbacks: dict[str, bool]) -> dict[str, bool]:
    return {name: resolve_feature_value(values.get(name), fallbacks[name]) for name in fallbacks}
