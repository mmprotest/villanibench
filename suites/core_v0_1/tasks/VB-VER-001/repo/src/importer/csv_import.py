def import_users(lines: list[str]) -> list[dict[str, str]]:
    users: list[dict[str, str]] = []
    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            # BUG: one bad row stops the entire import.
            break
        users.append({"name": parts[0], "email": parts[1]})
    return users
