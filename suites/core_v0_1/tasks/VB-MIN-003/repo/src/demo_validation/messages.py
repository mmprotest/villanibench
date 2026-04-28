EMPTY_PROJECT_NAME = "Project name cannot be blank"


def validate_project_name(name: str) -> str | None:
    if not name or not name.strip():
        return EMPTY_PROJECT_NAME
    return None


def validate_many(names: list[str]) -> list[str | None]:
    return [validate_project_name(name) for name in names]
