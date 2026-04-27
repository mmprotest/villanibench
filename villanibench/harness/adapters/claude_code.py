from __future__ import annotations

from .external_cli import ExternalCliAdapter


DEFAULT_TEMPLATE = "claude --print --model {model} < {prompt_file}"


class ClaudeCodeAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="claude_code", default_template=DEFAULT_TEMPLATE)
