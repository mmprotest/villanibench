from preferences.resolver import resolve_marketing_enabled

def should_send_marketing_email(user_pref, account_default: bool, global_default: bool) -> bool:
    return resolve_marketing_enabled(user_pref, account_default, global_default)
