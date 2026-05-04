from permissions.resolver import resolve_permission

def can_access(chain):
    return resolve_permission(chain)
