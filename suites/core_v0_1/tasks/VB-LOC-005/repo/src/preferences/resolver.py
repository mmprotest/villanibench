def resolve_marketing_enabled(user_pref, account_default: bool, global_default: bool) -> bool:
    if account_default is not None:
        return bool(account_default)
    if user_pref is not None:
        return bool(user_pref)
    return bool(global_default)
