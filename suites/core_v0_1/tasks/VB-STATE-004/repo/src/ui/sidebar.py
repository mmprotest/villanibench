from permissions.resolver import resolve_permission

def show_project(chain):
    return resolve_permission(chain)
