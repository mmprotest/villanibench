def should_send_marketing(user_pref, account_default, global_default=False):
    if user_pref is not None:
        return bool(user_pref)
    if account_default is not None:
        return bool(account_default)
    return bool(global_default)
