from preferences.resolver import should_send_marketing


def marketing_allowed(user_pref: bool | None, account_default: bool, global_default: bool = False) -> bool:
    return should_send_marketing(user_pref, account_default, global_default)
