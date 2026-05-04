from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .external_cli import ExternalCliAdapter


OPENCODE_PROVIDER_ID = "villani-local"
OPENCODE_API_KEY_ENV = "VILLANI_OPENCODE_API_KEY"

DEFAULT_TEMPLATE = (
    'opencode run "{prompt_text}" '
    '--model "{model}" '
    '--agent build '
    '--format json '
    '--dangerously-skip-permissions'
)


def _normalise_base_url(base_url: Any) -> str | None:
    if base_url is None:
        return None

    value = str(base_url).strip()
    if not value:
        return None

    if not value.rstrip("/").endswith("/v1"):
        value = value.rstrip("/") + "/v1"

    return value


def _raw_model_id(model: Any) -> str:
    value = str(model).strip()

    prefix = f"{OPENCODE_PROVIDER_ID}/"
    if value.startswith(prefix):
        value = value[len(prefix):]

    if not value:
        raise ValueError("OpenCode model cannot be empty")

    return value


def _qualified_model_id(model: Any) -> str:
    return f"{OPENCODE_PROVIDER_ID}/{_raw_model_id(model)}"


def _write_project_opencode_config(
    *,
    cwd: Path,
    model: str,
    base_url: str,
    api_key_env: str = OPENCODE_API_KEY_ENV,
) -> str:
    raw_model = _raw_model_id(model)
    qualified_model = _qualified_model_id(raw_model)

    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": qualified_model,
        "provider": {
            OPENCODE_PROVIDER_ID: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Villani Local",
                "options": {
                    "baseURL": base_url,
                    "apiKey": f"{{env:{api_key_env}}}",
                },
                "models": {
                    raw_model: {
                        "name": raw_model,
                    },
                },
            },
        },
    }

    cwd.mkdir(parents=True, exist_ok=True)
    config_path = cwd / "opencode.json"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return qualified_model


class OpenCodeAdapter(ExternalCliAdapter):
    def __init__(self) -> None:
        super().__init__(name="opencode", default_template=DEFAULT_TEMPLATE)

    def prepare(self, task, sandbox_dir: Path, config: dict) -> None:
        base_url = _normalise_base_url(config.get("base_url"))
        if base_url is None:
            return None

        model = config.get("model")
        if not model:
            raise ValueError("OpenCode adapter requires model when base_url is set")

        cwd = (sandbox_dir / "repo").resolve()

        qualified_model = _write_project_opencode_config(
            cwd=cwd,
            model=str(model),
            base_url=base_url,
        )

        # This is the critical mutation. ExternalCliAdapter.run() later reads
        # config["model"] when rendering the command template.
        config["model"] = qualified_model

        return None