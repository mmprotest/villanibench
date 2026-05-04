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
        value = value[len(prefix) :]

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

    def prepare_template_vars(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        ExternalCliAdapter should call this before formatting DEFAULT_TEMPLATE.

        Required incoming values:
          - cwd
          - model
          - prompt_text

        Optional incoming values:
          - base_url
          - api_key
          - env

        If base_url is present, this writes cwd/opencode.json and rewrites
        model to villani-local/<raw-model-id>, forcing OpenCode to use the
        benchmark's local OpenAI-compatible endpoint instead of hosted inference.
        """
        result = dict(values)

        cwd = result.get("cwd")
        model = result.get("model")
        base_url = _normalise_base_url(result.get("base_url"))
        api_key = result.get("api_key") or "dummy"

        env = dict(result.get("env") or os.environ)
        env.setdefault(OPENCODE_API_KEY_ENV, str(api_key))
        result["env"] = env

        if base_url is not None:
            if not cwd:
                raise ValueError("OpenCode adapter requires cwd when base_url is set")
            if not model:
                raise ValueError("OpenCode adapter requires model when base_url is set")

            result["model"] = _write_project_opencode_config(
                cwd=Path(cwd),
                model=str(model),
                base_url=base_url,
            )

        return result