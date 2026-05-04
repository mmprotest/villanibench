from .base import RunnerAdapter
from .claude_code import ClaudeCodeAdapter
from .minimal_react_control import MinimalReactControlAdapter
from .opencode import OpenCodeAdapter
from .pi import PiAdapter
from .qwen_cli import QwenCliAdapter
from .villani import VillaniAdapter


def build_adapter(name: str) -> RunnerAdapter:
    normalized = "minimal_react_control" if name == "react" else name
    if normalized == "minimal_react_control":
        return MinimalReactControlAdapter()
    if normalized == "villani":
        return VillaniAdapter()
    if normalized == "opencode":
        return OpenCodeAdapter()
    if normalized == "claude_code":
        return ClaudeCodeAdapter()
    if normalized == "pi":
        return PiAdapter()
    if normalized == "qwen-cli":
        return QwenCliAdapter()
    raise ValueError(f"Unknown runner: {name}")
