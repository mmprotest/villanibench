import warnings


def maybe_warn_deprecated(config: dict[str, object]) -> None:
    if "new_timeout" in config:
        warnings.warn("new_timeout is deprecated", DeprecationWarning, stacklevel=2)
