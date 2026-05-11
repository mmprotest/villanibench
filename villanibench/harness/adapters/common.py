from __future__ import annotations

import os
import shutil


def resolve_executable_for_sandbox(command: str, env: dict[str, str] | None = None) -> str:
    if os.path.isabs(command):
        if not os.path.exists(command):
            raise RuntimeError(
                "Agent executable could not be resolved before sandbox launch: "
                f"{command}. The sandbox user does not inherit your interactive shell profile. "
                "Use an absolute executable path or install the agent in a system-visible location."
            )
        return command

    resolved = shutil.which(command, path=(env or {}).get("PATH"))
    if not resolved:
        raise RuntimeError(
            "Agent executable could not be resolved before sandbox launch: "
            f"{command}. The sandbox user does not inherit your interactive shell profile. "
            "Use an absolute executable path or install the agent in a system-visible location."
        )
    return os.path.abspath(resolved)
