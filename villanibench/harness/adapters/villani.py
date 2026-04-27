from __future__ import annotations

from .external_cli import ExternalCliAdapter


DEFAULT_TEMPLATE = "villani-code run --prompt-file {prompt_file} --cwd {cwd} --model {model} --base-url {base_url} --api-key {api_key}"


class VillaniAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="villani", default_template=DEFAULT_TEMPLATE)
