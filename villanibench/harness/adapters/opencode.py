from __future__ import annotations

from .external_cli import ExternalCliAdapter


DEFAULT_TEMPLATE = "opencode run --model {model} --cwd {cwd} --prompt-file {prompt_file}"


class OpenCodeAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="opencode", default_template=DEFAULT_TEMPLATE)
