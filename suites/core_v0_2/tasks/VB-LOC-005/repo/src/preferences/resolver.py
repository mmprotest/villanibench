def should_send_marketing(user_pref: bool | None, account_default: bool, global_default: bool = False) -> bool:
    # BUG: account default overrides explicit user opt-out.
    if account_default is not None:
        return bool(account_default)
    if user_pref is not None:
        return bool(user_pref)
    return bool(global_default)
