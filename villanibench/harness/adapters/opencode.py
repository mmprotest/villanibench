from __future__ import annotations

from .external_cli import ExternalCliAdapter


DEFAULT_TEMPLATE = "opencode run {prompt_text} --model {model} --cwd {cwd}"


class OpenCodeAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="opencode", default_template=DEFAULT_TEMPLATE)
