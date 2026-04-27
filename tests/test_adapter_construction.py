from villanibench.harness.adapters import build_adapter
from villanibench.harness.adapters.claude_code import DEFAULT_TEMPLATE as CLAUDE_DEFAULT
from villanibench.harness.adapters.opencode import DEFAULT_TEMPLATE as OPENCODE_DEFAULT
from villanibench.harness.adapters.villani import DEFAULT_TEMPLATE as VILLANI_DEFAULT


def test_adapter_construction_and_defaults():
    assert build_adapter("opencode").default_template == OPENCODE_DEFAULT
    assert build_adapter("claude_code").default_template == CLAUDE_DEFAULT
    assert build_adapter("villani").default_template == VILLANI_DEFAULT
    assert build_adapter("react").name == "minimal_react_control"
