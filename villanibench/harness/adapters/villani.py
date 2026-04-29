from __future__ import annotations

from .external_cli import ExternalCliAdapter


DEFAULT_TEMPLATE = (
    'villani-code run '
    '--repo "{cwd}" '
    '--provider openai '
    '--model "{model}" '
    '--base-url "{base_url}" '
    '--api-key "{api_key}" '
    '--auto-approve '
    '--auto-accept-edits '
    '--dangerously-skip-permissions '
    '--debug trace '
    '--debug-dir "{output_dir}/villani_debug" '
    '"{prompt_text}"'
)


class VillaniAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="villani", default_template=DEFAULT_TEMPLATE)
