from .config import DEFAULT_RETRIES


def build_help_text() -> str:
    return f"--retries (default: {DEFAULT_RETRIES})"
