import warnings


def maybe_warn_deprecated(config: dict[str, object]) -> None:
    if "old_timeout" in config:
        warnings.warn("old_timeout is deprecated", DeprecationWarning, stacklevel=2)
